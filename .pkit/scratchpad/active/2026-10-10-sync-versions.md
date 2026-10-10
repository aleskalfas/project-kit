---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-10
---

# Only an upgrade moves a project's versions

A design for #1429. It sets the shape of the maintainer's decision that `pkit sync` never moves a version and that every migration runs inside an upgrade.

- **The direction is decided:** by the maintainer on 10 October, on PR #1395. This note designs its shape and does not reopen it.
- **The starting point:** the critic's and the architect's reviews of that decision, kept as #1429's two comments. Their findings were checked against the code here, and the design corrects them where the code disagrees ("Corrections to the reviews").
- **Read from main at `e2f0a533`:** the code, the records, the migrations and the tests below.
- **Citations:** records by id and point or section. Code by file and function. A line number, where one helps, is at `e2f0a533`.
- **Shared with #1394's design** (`.pkit/scratchpad/active/2026-10-09-content-upgrades.md`): COR-001's named-writer principle, COR-004's list of operations, COR-010, COR-017 and ADR-049. Each is written once. Whichever design's record lands first carries the principle, and the other adds its instance.
- **Its build** is ordered after #1410 and before #1444. It shares the version guard with #1435, the messages of upgrade and sync with #1438, and status with #1436 and #1440 ("Slicing").

## The question

How does a project move from one version to the next so that every migration runs exactly where the move happens, and nothing else moves a version?

## In short

`pkit sync` keeps a project in line with the release it records. `pkit upgrade` is the one operation that moves the recorded versions, and it runs every migration.

- **One propagation step, two callers:** sync runs it at the project's version, and upgrade at its target. The stop on a version mismatch belongs to the sync command, never to the step.
- **Sync writes no project-owned path:** methodology files, the deployed harness, the rendered ignore file, the workspace and provisioning. Merge and seeding leave it, if the maintainer agrees (questions 5 and 8).
- **A version per component:** the backbone and each adapter and kit-shipped capability. Sync checks the backbone's, and skips and reports a component whose bundled version differs.
- **Two recorded states:** an upgrade records its target before it writes anything and its completion last. An interrupted upgrade is finished by the next one, and a newer release's content stops an older pkit.
- **Recovery:** a project whose migrations were stranded runs every backbone migration once, on its first upgrade under the new release (question 3).
- **A stop that names the remedy:** each state of a mismatch has its own remedy. `pkit upgrade` is wrong in two of them.
- **Every migration inside the transition,** in COR-010's order: backbone, then adapters, then capabilities in dependency order. Adapter migrations, which have never run in an adopter, start running.
- **Records:** a new core record holds the principle and partially supersedes COR-017. COR-001, COR-004 and COR-010 are refined, and ADR-049's recovery claim is corrected in place.

## The direction, and two claims in its wording

The maintainer's comment of 10 October on PR #1395 decided:

> Sync makes the project match the pkit that runs it at the project's version: it restores the methodology's files, re-wires the harness, recreates the workspace and provisions query commands. It runs no migration and writes no project-owned path, so COR-001's extension contract stays true as written. When the running pkit is newer than the project's content, sync stops and names pkit upgrade, as it already stops when pkit is older (#1212). Only upgrade moves versions, and every migration, backbone and capability, runs there. [...] Pinned projects, the default, see no change.

The direction stands. Two claims in its wording do not hold today, and the design makes the first true:

- **"Writes no project-owned path":** today sync also writes `.claude/settings.json` and `CLAUDE.md` through the merge primitives, recreates missing seed paths and writes the manifest. The design takes each out of sync, so the claim becomes true (questions 5 and 8, "What sync writes").
- **"Pinned projects, the default, see no change":**
  - **Pinning is the default only after an upgrade.** `pkit init` writes no pin (ADR-049 point 2, `install.install_kit`). An upgrade pins by default (ADR-049's amendment).
  - **Some pinned projects do see a change,** and it is a fix. Under the router's offline fallback, or with content behind its pin, sync moves content past the pin today. After the change it stops ("On a mismatch").

## Today

### Every path that moves a version

- **`pkit sync`** (`sync.run_sync`):
  - copies the running pkit's methodology trees over the project's
  - refreshes each kit-shipped capability through `capabilities.refresh_capability`, which runs the capability's pending migrations, copies its tree and restamps its version
  - records the running pkit's version as `backbone_version` (`sync._update_recorded_backbone_version`)
  - runs no backbone migration and no adapter migration
- **`pkit upgrade`** (`upgrade.run_upgrade`) returns early when `backbone_version` equals the running version (line 190). Otherwise it runs `run_sync`, then the backbone migrations, then the adapters' (lines 213 to 217).
- **`pkit capabilities upgrade <name>`** (`cli.upgrade_capability_cmd`) refreshes one capability through the same `refresh_capability`, after its collision and dependency checks.
- **`pkit pin <newer>`** and a pinned upgrade run the target release's `upgrade` through the router's bypass (`upgrade.reconcile_forward_via_target`, `router.run_bypassed`).
- **`pkit capabilities install`** copies the running pkit's capability at whatever version it ships. It checks only that the capability's `requires_backbone` admits the project's recorded backbone (`cli._check_backbone_satisfied`).

### Where migrations strand

- **Backbone migrations strand after a sync.** Sync records the new `backbone_version` and runs none of them. A later upgrade finds the project at its target and returns early.
- **They strand inside an upgrade too.** The version is recorded by `run_sync` before the migrations run. An upgrade interrupted during its migrations leaves the project at its target, and the re-run returns early.
- **So ADR-049's recovery claim does not hold.** Point 1 says a re-run "is idempotent (sync re-applies content, migrations detect already-applied state and no-op per COR-010, and the pin flip is a no-op once it matches)". The CLI reference repeats it (`.pkit/cli/README.md`, `upgrade`). The re-run never reaches the migrations.
- **Adapter migrations have never run in an adopter.** Two causes, either enough:
  - `install._install_adapter` copies an adapter's README, package metadata, top-level scripts and settings. It never copies `migrations/`, so `upgrade._run_component_migrations` finds no scripts in the project's copy.
  - No code writes an adapter's per-component manifest (`.pkit/adapters/<name>/project/manifest.yaml`). The runner skips an adapter without one.
  - The only adapter migration, claude-code's `0.5.0/001`, wires the `CLAUDE.md` include. `merge-claude-md.sh` does the same on every sync, so nothing visible broke.
- **A capability's migrations run before its files are copied,** inside sync (`refresh_capability`). COR-010's order puts propagation first and component migrations after the backbone's (COR-010, "Cross-tier upgrade requires explicit compatibility resolution").
- **Eight backbone scripts in seven version directories** ship today. Two in `1.150.0/` share the index `001`, so their order comes from their slugs.

### What sync writes

| What | Whose | How today |
|---|---|---|
| `.pkit/<area>/core/`, flat area files, adapters, `cli/pkit` | the methodology's | copied over (`install._install_area`) |
| each kit-shipped capability's tree, except its `project/` | the methodology's | copied, after its migrations |
| `.claude/settings.json`, `CLAUDE.md` | the project's | merge primitives on every sync (`install._ADAPTER_PRIMITIVES`) |
| a missing `project/` stub, a missing `.pkit/agents/project/overlay.yaml` | the project's | recreated (`_install_area`, tests `test_sync_stubs_project_dir_for_area_that_landed_after_install` and `test_sync_seeds_agents_overlay_if_missing`) |
| `.pkit/manifest.yaml` | the project's | `backbone_version` set, or a minimal manifest seeded where none exists |
| per-capability `manifest.yaml` | the project's | restamped with the new version |
| project-owned files a capability migration writes | the project's | e.g. project-management `0.55.0/004` writes `.pkit/project/config.yaml` |
| `.claude/skills`, `.claude/agents` deployments | derivable | deploy primitives |
| `.pkit/.gitignore` | the methodology's, rendered whole (ADR-009 rule 7) | rendered |
| `.agent-workspace/`, `.git/info/exclude` | clone-local | created where missing |
| query-command environments | outside the repository | provisioned |

- **Merge inside sync contradicts two documents.** COR-004 keeps sync and merge apart for their consent profiles ("`sync` and `merge` stay separate"). The CLI reference says sync "Does **not** invoke seed [...] or merge".
- **The capability migrations make COR-048 point 1 false in sync,** and project-management's `0.55.0/004` claims "the upgrade being the consent" while sync runs it.

### The pinned flows

- **The routed child.** When a pinned project's `pkit upgrade` runs under its pin's code, `upgrade._auto_advance_pinned` compares the latest release with the pin only. At "latest equals pin" it returns, whatever the project's content holds (lines 553 to 555).
- **Content behind the pin** (a hand-edited pin, a bad merge): sync under the pin's code moves the content to the pin and runs no backbone migration. Upgrade there brings it forward only when a newer release exists.
- **The router's offline fallback** (`router._run_pinned`): when the pin cannot be fetched, the installed pkit runs instead.
  - **A newer installed pkit's sync** moves the content past the pin (`test_sync_newer_than_the_content_moves_it_forward`). That is the hazard ADR-049 named, and it stays possible.
  - **Its upgrade** is no routed child, so it takes the unpinned path and raises the pin to the installed version (`run_upgrade`, lines 224 and 225). ADR-049 point 5 says an offline pinned upgrade leaves the pin unchanged.
- **#1212 is not yet released.** Its changeset is in `.changes/unreleased/` (`backbone-patch-20261001-180000-older-pkit-refuses-downgrade.yaml`). Every released pkit, 1.149.0 included, writes its older content over a newer project without a word.

### Versions a release ships

- **Tagged installs:** a release's content is tied to its code (ADR-033). So a pkit at a tagged version ships one version of every adapter and capability.
- **Component-only releases cut no tag** (`.pkit/release/README.md`, "A component-only release (no backbone move) cuts no tag").
- **Untagged installs:** `pkit init` recommends `uv tool install git+ssh://…/project-kit.git` with no tag (`install._print_next_steps`, the CLI reference's "Installing pkit on PATH"). That installs main's head. Its `VERSION` is the last release's, while its files and its components may be newer.

## Forces

- **The maintainer's direction:** sync moves no version and runs no migration, and upgrade runs every migration.
- **COR-010's order:** compatibility, propagation, backbone migrations, component migrations, derivable state, recorded versions.
- **COR-004's consent rule:** one command, one operation. Upgrade today anchors to no operation on COR-004's list.
- **Older code meets newer state.** A pinned project's next command may run an older release's code over what a newer one left. Only state that older code already reads stops it.
- **Pipelines.** A pipeline runs `pkit sync` on checkout, before its gate (the lifecycle README, "How dependencies are provisioned before an offline run"). A stop fails it.
- **Offline use.** "A degraded-but-running command beats a broken one" (ADR-039 D2).
- **Idempotence.** COR-010 promises "already-applied state is a no-op". Recovery that re-runs scripts leans on it.

## The design

### One propagation step, two callers

`run_sync` splits into a propagation step and the sync command. Upgrade calls the step, never the command, so the stop never fires inside an upgrade (the critic's first red flag, removed by construction).

| | `pkit sync` | the version transition's step |
|---|---|---|
| Content | the running pkit's, which must be the project's recorded version | the running pkit's, which is the target |
| Guard | stops unless the running version is the recorded one and the last transition completed | refuses an older running pkit (#1212) |
| Methodology trees | copied | copied |
| A kit-shipped capability | copied when its bundled version is the recorded one, else skipped and reported | copied, unless held back |
| Merge delivery | no (question 5) | yes |
| Seeds | none (question 8) | an area or component new to the project |
| Migrations | never | backbone, adapters, capabilities |
| Recorded versions | none written | target first, completion last |
| Derivable state | regenerated | regenerated |

- **The self-host branch comes first in both,** unchanged (ADR-059 point 2).
- **The step checks no version and runs no migration.** Each caller does what the table says around it.
- **The stop's message names the remedy** for the state it finds ("On a mismatch").

### What sync writes

After the change, sync writes no project-owned path.

- **Methodology files:** the methodology's trees and each kit-shipped capability at its recorded version, its `project/` left alone.
- **Derivable or clone-local state,** which COR-010 already allows a setup primitive to regenerate ("Manifest content: non-derivable state only"):
  - the deployed harness, by the deploy primitives only
  - `.pkit/.gitignore`, rendered whole
  - the agent workspace and its line in `.git/info/exclude`
  - the query commands' environments
- **No longer:** merge (question 5), seed recreation (question 8), any manifest write, any migration.
- **What this makes true:** COR-001's "project-owned paths are not touched by sync" and its seeding contract hold as written. COR-004's "`sync` and `merge` stay separate" holds. COR-001's "never reads" still goes, by #1432, since validation reads.

### The versions a project records, and what current means

| Component | Recorded in | Moved by |
|---|---|---|
| backbone, its files | `backbone_version` in `.pkit/manifest.yaml` | a transition, first |
| backbone, its migrations | a new optional key, `migrated_version` (name provisional) | a transition, last |
| each adapter | its per-component manifest, written for the first time | a transition, after the adapter's migrations |
| each kit-shipped capability | its per-component manifest | a transition, after the capability's migrations |
| an incubated capability | its own `package.yaml` | the project (COR-031) |
| an externally-sourced capability | its pin (COR-041) | an upgrade, by repointing the pin |

- **Current for sync:** the running pkit's version equals `backbone_version`, and `migrated_version` equals it too. Anything else stops sync.
- **Inside a sync that proceeds, each component:**
  - bundled version equal to the recorded one: copied, no migration, no stamp
  - bundled newer: skipped and reported, "pending: run `pkit upgrade`"
  - bundled older: skipped and reported, with no override (today's #524 guard, without `--force`)
  - not in the bundle: the orphan warning, as today
  - incubated: skipped, with the collision report of COR-031, as today
  - externally-sourced: brought to its pin, once its fetch is built (COR-041). Today `_sync_installed_capabilities` has no branch for it
  - recorded version unreadable: skipped and reported
- **Current for upgrade, its early return:** `backbone_version` and `migrated_version` both equal the target, and every adapter and kit-shipped capability records its bundled version. Today only the backbone is compared (line 190), which is how adapter migrations would strand even if they ran.
  - **A capability held back** fails the test, so the next upgrade tries it again and reports it again. It writes nothing else.
- **What a version identifies:** content only for a tagged install. An untagged install keeps the last release's `VERSION` over newer files, so sync's check passes while the files differ (question 9).

### How an upgrade records its progress

An upgrade writes the target to `backbone_version` before it writes anything else, and writes `migrated_version` last (question 2).

1. **Compatibility,** as today, against the versions each component moves to.
2. **The target is recorded:** `backbone_version` becomes the target. `migrated_version` keeps its value, or stays missing.
3. **Propagation** at the target.
4. **Migrations:** the backbone's from `migrated_version` to the target, then each adapter's and each capability's from its own recorded version. Each component is restamped when its migrations finish.
5. **Merge and derivable state.**
6. **Completion:** `migrated_version` becomes the target.
7. **The pin,** last, as ADR-049 point 1 sets.

- **The transition is complete when the two keys are equal.** A missing `migrated_version` reads as incomplete with no lower bound. No project at the new release's content can lack it: the release's `init` and its upgrades write it.
- **An interrupted upgrade is finished by the next one.** It finds the two keys apart, runs the backbone migrations from `migrated_version`, and each component's from its own record.
- **Why the target is written first:** an older pkit reading an interrupted upgrade.
  - **Written last,** the record would show the older pkit its own version. It would pass #1212's guard and copy its older files over a half-migrated tree.
  - **Written first,** the record shows a newer version. The older pkit refuses (#1212), and its message leads to the newer code.
  - **A marker the older code cannot read** would not stop it. That is why a second recorded state beats an "in progress" marker.
- **The limit:** the protection starts with the release that ships #1212. A project pinned at 1.149.0 or earlier runs code without the guard. If its first upgrade out is interrupted, a `pkit sync` under the old pin copies 1.149.0's files back. The next `pkit upgrade` still recovers it, through the replay below.
- **No schema bump:** the key is optional, and no JSON schema describes the manifest. `manifest.write_backbone_manifest` keeps keys it does not know when it updates a file, so an older writer leaves the key in place. A test holds that.
- **`pending_migration_scripts` takes `migrated_version` as its lower bound** for the backbone, in place of `backbone_version`.

### Projects already stranded

A missing `migrated_version` means the project's migration history is unknown. The first upgrade under the new release then runs every backbone migration up to its target, once (question 3).

- **What leans on it:** COR-010's idempotence. A replay also runs scripts on states that never needed them, and on states a project changed after a script ran. So it needs more than "already-applied state is a no-op".
- **The contract it needs:** a backbone script leaves unchanged a state that never needed it. A test runs every backbone script on a fresh install at the current version and requires no change.
- **The audit of today's eight scripts:**
  - **No effect on a fresh state:** `1.0.0/001` and `1.31.0/001` remove leftovers, `1.32.0/001` retires the bundle pattern, `1.93.0/001` exits when the rules area exists, and `1.140.0/001` only prints guidance.
  - **Can re-add what a project removed later:**
    - `1.54.0/001` appends an overlay category the project deleted after the script ran.
    - `1.150.0/001-keep-process-journal-logging` writes `enabled: true` where the `process` block was removed while old journals stay on disk.
    - `1.150.0/001-untrack-runtime-ignored-files` stages again the untracking of a declared file a project forced back into git.
- **Capabilities are never replayed.** Their per-component manifest is written at install and restamped after their migrations, so their history is known.
  - **An unreadable capability version is held back and reported, not replayed.** project-management's `0.54.0/001` would grandfather a bootstrap that never happened. Today `refresh_capability` does replay it, since `pending_migration_scripts(None)` returns every script.
- **Adapters have no record yet.** The first transition under the new release runs claude-code's `0.5.0/001` from the bundle, which is safe on any state, and writes each adapter's manifest.
- **The dry run lists the replay,** and the changelog says why it runs once.

### On a mismatch

When the running version differs from the project's recorded version, or the last transition is incomplete, sync stops. It writes nothing, exits non-zero, refuses under `--dry-run` too, and takes no override, as #1212's refusal does.

- **The guard is one function,** `sync.refuse_content_downgrade` widened to both directions and to an incomplete transition. Sync, `capabilities install` and `upgrade` (question 6), and the conversion command (#1435) call it.
- **The gate reads the recorded content version only.** The pin chooses the message.

| State | Sync | The message names |
|---|---|---|
| Unpinned, running pkit newer | stops | **Move:** `pkit upgrade`, which pins by default (`--no-pin` to stay unpinned) and on a terminal may first update the tool (`--no-self-update`). **Stay:** `pkit pin`, which pins at the content's version, so the router runs it. **A pipeline:** commit a pin, or install the project's version, `uv tool install --force <url>@v<version>` |
| Pinned, the router fell back to another installed pkit | stops | reconnect and re-run, since the router runs the pin when it can fetch it, or `uvx --from <url>@v<pin> project-kit sync`. Not `pkit upgrade` |
| Pinned, content behind the pin, the pin's code running | stops | `pkit upgrade` (with the routed child's fix below) |
| Transition incomplete | stops | `pkit upgrade` |
| No manifest, or a recorded version that is no version | stops | `pkit upgrade`, which seeds the manifest at its target and replays every migration once |
| Running pkit older than the content or the pin | refuses, as #1212 does | unchanged. Content ahead of its pin also names `pkit upgrade`, which finishes the interrupted raise |

- **Upgrade under the router's fallback refuses too.** Today it raises the pin to the installed version. ADR-049 point 5 says an offline pinned upgrade leaves the pin unchanged, so the refusal makes the code honour it. A run is a fallback when the project pins a version, the running version differs, and the run is neither the routed child nor bypassed.
- **The routed child finishes its own pin before it looks at the latest release.**
  - **Latest is newer and resolvable:** it hands over to the latest, as today. The latest's upgrade finishes everything from the recorded states.
  - **Otherwise,** at latest, ahead of it, or offline: when the content is behind the pin or the transition incomplete, it runs the transition to its own pin in its own process. It already runs the pin's code.
  - **Content ahead of the pin and offline:** it says so, and names reconnecting.
  - **Its rollout:** the fix lives in the routed child's code, so a project pinned below the release that ships it gets it on its next raise past that release.
- **Messages that send an operator to sync to seed or repair the manifest** name upgrade instead: `run_upgrade` (missing manifest), `upgrade._require_backbone_version`, `upgrade._pin_order`, and `validate.py`'s missing-manifest diagnosis.
- **Messages that name `pkit sync` as a routine fix stay.** Where sync can run, they are right. Where it stops, its own message names the remedy.
- **Pipelines:** a pipeline that runs another pkit than the project's already validates with the wrong code (ADR-049 point 4). The stop surfaces that.
  - **The distribution URL is `git+ssh`** (`router.DISTRIBUTION_GIT_URL`). A pinned pipeline without SSH keys falls back and meets the stop. Installing the pin's version makes the router run itself, with no fetch.
  - **project-kit's own pipelines are unaffected:** they run self-host sync (`.github/workflows/checks.yml`, `friction-report.yml`).
- **A deploy-only mode** is question 10.

### Every migration inside the transition, and its order

The transition runs every migration, in COR-010's order. Sync runs none.

1. **Propagation:** the methodology's trees and every kit-shipped component, except one held back. The step also renders `.pkit/.gitignore`, as sync does today.
2. **Backbone migrations,** from `migrated_version`.
3. **Adapter migrations,** each from its recorded version, read from the bundle as capability migrations are, since the project's copy has no `migrations/`.
4. **Capability migrations,** dependencies first by their `requires_capabilities` (COR-030). Today they run in the manifest's order.
5. **Merge delivery, then derivable state,** regenerated again.
6. **Completion,** then the pin.

- **A capability's files are copied before its migrations,** as COR-010's order sets. Today `refresh_capability` runs them first.
  - **The audit of the eleven capability scripts and the adapter's one:** evidence's `0.2.0/001` removes the old flat skill files before the copy. Under the new order the copy removes them first, so the script finds nothing to do. project-management's `0.12.0/001` and `0.55.0/001` handle both orders. The rest read only project-owned files or fixed checksums, and the adapter's edits only `CLAUDE.md`.
- **`pkit capabilities upgrade <name>`** becomes a transition of one component: copy, migrate, stamp.
- **The dependency check reads the versions the transition installs,** not the installed ones (`upgrade._check_capability_dep_conflicts_for_upgrade`). #1410 changes this check first.
- **A new collision holds a capability back.** COR-017 says sync refuses the upgrade of a capability that would bring a new collision and names `pkit capabilities upgrade X --interactive`. Sync's refresh never built that, while `capabilities upgrade` did (`capabilities.detect_upgrade_collisions`). The transition takes it over: it holds the capability back, reports it, and names the interactive upgrade.
- **Derivable state a migration reads must be current when it runs.** `1.150.0/001-untrack-runtime-ignored-files` reads `.pkit/.gitignore` as rendered before the migrations. Its sibling `keep-process-journal-logging`, run first, can change what that render should hold ("Found on the way", 3). The ADR settles which render a migration may read.

### Capability install, capability upgrade, and other sources

- **`pkit capabilities install` and `upgrade` call sync's guard** (question 6). Every kit-shipped file a project holds then comes from the release its backbone records, except a capability a transition held back.
- **`pkit capabilities register`** copies nothing, so it needs no guard.
- **An externally-sourced capability** already follows the principle: sync brings its copy to its pin, and an upgrade repoints the pin (COR-041). When sync stops, nothing is fetched.

### `sync --force` and dry runs

- **`--force`'s only effect, copying an older capability over a newer one, moves a version down.** Sync stops doing it (question 11).
- **Dry runs:** sync's stop refuses under `--dry-run`, as #1212's does. Upgrade's dry run lists the target, the replay where the key is missing, each component's migrations, and what it would hold back.

### Messages and status

- **Status** shows an incomplete transition and each component a transition would move or held back, beside the backbone line it has (`status._report_backbone_version`). #1436 and #1440 extend status too.
- **The CLI reference's upgrade entry** says migrations run "then runs `sync`". The code runs sync first. The rewrite follows the design.

### The records it changes

- **A new core record,** "A project stays at its version until an upgrade moves it" (title provisional):
  - a project records a version for its backbone and for each component it installs
  - reconciliation runs at the recorded versions, moves none, and runs no migration
  - a version transition is the only operation that moves a recorded version, and every migration runs inside it
  - a transition records its target before it writes anything and its completion last, and the next transition finishes an incomplete one
  - a transition moves every kit-shipped component, except one it holds back for a reason it reports
  - a command that writes methodology content under another version than the project records stops and names the remedy, and read-only commands still run
  - it cites COR-041 as precedent, partially supersedes COR-017, and uses core terms only
- **COR-001, refined:** sync's and the transition's instances of the named-writer principle. If #1432 has not landed, this states the principle.
- **COR-004, refined:** its list of operations gains the version transition (question 1).
- **COR-010, refined:** Update runs at the recorded versions, and the transition records its target first and its completion last.
- **COR-048 point 1,** refined in place: an upgrade does write the configuration file, through the migrations point 5 allows ("Found on the way", 8).
- **The realising ADR,** by the architect, once the core record is accepted: the split, the per-component table, the manifest key and its test, the replay and its test, the routed child's order, the fallback refusal, the messages, the migration order, `--force`, and the tagged install.
- **ADR-049, refined in place, not superseded.** Its decision stands: the pin flips last, and no two-phase commit. Only its claim of how a re-run recovers was false, and the decisions README fixes a false fact in place.
- **ADR-044:** its D1 and Implications say an offline upgrade goes on to "sync the project from the current bundle". They name the transition.
- **Unchanged:** COR-030, COR-031, COR-041, ADR-033, ADR-039 and ADR-059.

## Questions for the maintainer

One decision each, in order of consequence. Each has a recommendation, the alternative, and the main cost of each.

### 1. Is `pkit upgrade` one operation, a version transition?

- **The question:** COR-004 says a command performs one operation, and rejects an "update" that does sync, merge and migrations. Should its list gain the *version transition* as one operation?
- **Example:** `pkit upgrade` from 1.149 to 1.150 copies 1.150's files, runs the migrations, merges the settings and pins the project. None of COR-004's operations names that.
- **Recommended:** yes. A version transition moves a project's recorded versions to a target. Running it is the one consent for its parts: the target's content, every pending migration with the writes COR-048 point 5 allows, merge delivery, the recorded versions and the pin.
  - `pkit upgrade`, `pkit capabilities upgrade <name>` and `pkit pin <newer>` anchor to it.
  - COR-004's rejected "smart update" is reworded: what it rejects is a verb that picks its operations by the state it finds.
  - The tool's self-update (ADR-044) acts on no project, so it stays outside the operation. The realising ADR names it as a step before the transition.
  - **Its cost:** a foundational record on the command surface changes, and one command carries several parts.
- **Alternative:** one operation per command, as COR-004 reads now: `pkit upgrade` copies and records, and a command of its own runs the migrations.
  - **Its cost:** a gap between the two commands, which is the stranding this design removes.

### 2. How does an upgrade record its progress?

- **The question:** how does the next run know whether the last upgrade finished?
- **Example:** an upgrade from 1.149 to 1.152 is interrupted during its migrations. Today the manifest already says 1.152, so the next `pkit upgrade` finds nothing to do.
- **Recommended:** two recorded states. `backbone_version` moves to the target first, and a new optional `migrated_version` is written last. The transition is complete when they are equal ("How an upgrade records its progress").
  - **Its cost:** a manifest key, and a rule that a missing key means incomplete. Pinned releases up to 1.149.0 lack #1212, so they are not stopped either way.
- **Alternative:** write `backbone_version` last, as COR-010's order reads, with an "in progress" marker.
  - **Its cost:** an older pkit cannot read the marker. It sees its own version, passes #1212's guard and copies its files over a half-migrated tree.

### 3. How do projects already stranded recover?

- **The question:** what does the first upgrade under the new release do for a project with no `migrated_version`?
- **Example:** an unpinned project at 1.53 synced by a 1.60 pkit records 1.60 without `1.54.0/001`. Its overlay lacks the architect's categories, and every later upgrade starts from 1.60.
- **Recommended:** a missing key means unknown, and the first upgrade runs every backbone migration up to its target, once. A new contract and a test hold that each backbone script leaves unchanged a state that never needed it ("Projects already stranded").
  - **Its cost:** every adopter's first upgrade runs eight scripts. Three of them can re-add what a project removed after they ran. Every future backbone script carries the stronger contract.
- **Alternative:** a missing key means complete. A stranded project recovers by a command that runs the backbone migrations from a version its operator names, which the changelog explains.
  - **Its cost:** a project stays stranded unless its operator knows which versions it skipped, and the files cannot tell.

### 4. Where does the principle live?

- **The question:** COR-017 says "Sync auto-upgrades installed capabilities". The design overturns that sentence, and the decisions README says an overturned decision is superseded by a new record. Which record carries the principle?
- **Example:** after the change, a reader of COR-017 learns that sync no longer moves a capability, and where the rule went.
- **Recommended:** a new core record carries the principle ("The records it changes") and partially supersedes COR-017. COR-001, COR-004 and COR-010 are refined and point to it.
  - **Its cost:** one more core record, and edits to three foundational ones.
- **Alternative:** COR-010 carries the principle as a refinement. A short new record only supersedes COR-017's paragraph.
  - **Its cost:** one principle split across two records, and COR-010's refinement grows past the lifecycle's list of operations.

### 5. Does merge leave sync?

- **The question:** should sync stop running the merge primitives?
- **Example:** every `pkit sync` runs `merge-settings.sh` and `merge-claude-md.sh`, which write `.claude/settings.json` and `CLAUDE.md`. Both files are the project's.
- **Recommended:** yes. Merge runs at init, in every version transition (where new baselines arrive), when a capability is installed or upgraded, and on `pkit merge`.
  - At an unchanged version merge has nothing new to add. It only re-adds what a project removed.
  - Sync then writes no project-owned path, as the decision says, and COR-004's "`sync` and `merge` stay separate" holds.
  - **Its cost:** a safety deny a project removed returns at the next merge or transition, not at the next sync (COR-002's baseline-enforce). Validation could report a missing safety entry, as a follow-up. project-kit's maintainers run `pkit merge` after editing a baseline, since the self-host sync stops merging too.
- **Alternative:** sync keeps merge, and COR-001, COR-004 and the CLI reference say that sync runs merge's auto-add tier.
  - **Its cost:** sync carries two consent profiles, and "writes no project-owned path" stays false.

### 6. Do `pkit capabilities install` and `upgrade` stop on a version mismatch?

- **The question:** should the two commands call sync's guard?
- **Example:** an unpinned project at 1.149 with a 1.152 pkit runs `pkit capabilities install living-docs`. It gets 1.152's living-docs beside 1.149's backbone, a mix no release shipped.
- **Recommended:** yes, with sync's remedies. Every kit-shipped file a project holds then comes from one release, except a capability a transition held back.
  - **Its cost:** someone with a newer pkit pins or upgrades before installing a capability.
- **Alternative:** they keep copying from the running pkit, checked only by `requires_backbone`.
  - **Its cost:** mixes no test covers, and a capability whose migrations assume a backbone the project never moved to.

### 7. Which changeset segment?

- **The question:** a minor or a major backbone changeset for the sync change?
- **Example:** an unpinned project's pipeline runs `pkit sync` with the latest pkit. It passes today and fails after the change.
- **Recommended:** minor, with a changelog entry under "Changed" that names the pipeline impact and the recipe: commit a pin, or install the project's version in the pipeline.
  - Projects upgraded since 1.145.0 are pinned by default, and see no change while their pin can be fetched.
  - **Its cost:** a command that worked fails, under a minor number.
- **Alternative:** major, since a working command now fails and COR-017's contract inverts.
  - **Its cost:** a major number for a change most adopters do not see.

### 8. Does sync recreate a missing seed path?

- **The question:** after install, may sync write a seed path the project no longer has?
- **Example:** delete `.pkit/agents/project/overlay.yaml` and run `pkit sync`, and the seed comes back. COR-001 says a seeded path is written once, at first install, and "Subsequent syncs do not touch this path".
- **Recommended:** no. A seed is written when the area or component that declares it first enters the project: at init, at a capability's install, or in the transition that brings a new area.
  - A seed the project deleted stays deleted. A command that needs it names its repair: `pkit agents reconcile --write` writes a missing overlay.
  - COR-001's extension contract stays true as written, as the decision says.
  - **Its cost:** sync repairs no deleted seed. The transition must tell an area new to the project from a deleted seed.
- **Alternative:** sync and the transition create a declared seed path that is missing and never write over one that exists. COR-001's seeding cadence says so.
  - **Its cost:** COR-001 changes, and a seed the project deleted on purpose returns on every sync.

### 9. What does a version name for an untagged install?

- **The question:** how is sync's check made honest when the running pkit was installed from no tag?
- **Example:** two machines install pkit with the recommended untagged command a week apart. Both report 1.149.0, but the second carries newer files and a newer capability. Sync's check sees no difference between them.
- **Recommended:** the realising ADR states that a version identifies content only for a tagged install. The recommended install becomes tagged: init prints `@v<its own version>`, the CLI reference follows, and #1376's test keeps the two equal.
  - **Its cost:** the printed command names a version that ages, and an untagged install stays possible and unchecked.
- **Alternative:** every release that moves a kit-shipped component also cuts a backbone patch and its tag (PRJ-002, PRJ-004).
  - **Its cost:** more releases, and still nothing for an install from a branch.

### 10. Does sync only stop on a mismatch, or also offer a deploy-only mode?

- **The question:** should a stopped sync have a mode that still deploys from the project's own files?
- **Example:** a fresh offline clone of a project pinned at 1.150, on a machine whose pkit is 1.152. The router cannot fetch 1.150 and runs 1.152, and sync stops.
- **Recommended:** stop only, for now. In the default shared visibility the deployed harness is committed (ADR-009), and provisioning needs the network anyway. An older installed pkit meets the same stop today (#1212). `--deploy-only` waits for a case that asks for it (COR-007).
  - **Its cost:** such a clone gets no agent workspace and no rendered ignore file until it can run its pin.
- **Alternative:** `pkit sync --deploy-only` runs the self-host branch's steps on any project: the project's own deploy primitives, the ignore render, the workspace and provisioning. It copies and records nothing.
  - **Its cost:** a third mode of sync now, and one release's Python steps run over another release's tree.

### 11. What happens to `pkit sync --force`?

- **The question:** how is `--force` retired?
- **Example:** today `--force` lets sync copy an older capability over a newer installed one, which moves its version down.
- **Recommended:** sync accepts `--force` for one release, ignores it and says so. A later change removes it with a guidance migration, as `1.140.0/001` did for the router shim.
  - **Its cost:** one release of a flag that does nothing.
- **Alternative:** remove it now.
  - **Its cost:** a pipeline that passes `--force` fails at once.

## Settled positions this reopens

Each accepted sentence below changes, for the maintainer's authorisation. The answers to questions 5 and 8 decide whether COR-001 and COR-004 change beyond this list.

1. **COR-017, "Lifecycle: install, sync, uninstall":** "**Sync** (`pkit sync`) auto-upgrades installed capabilities along with the rest of kit content." and "When sync would introduce a new collision [...], sync refuses to upgrade that specific capability and instructs the adopter to run `pkit capabilities upgrade X --interactive` to resolve."
   - **The change:** partially superseded. A version transition moves the capabilities, and a new collision holds a capability back there. Sync keeps a capability at its recorded version.
   - **With it:** the section's "Capabilities have an explicit install / sync / uninstall lifecycle", and the implication "**Sync extension** — refreshes installed capabilities; surfaces no-longer-shipped capabilities; refuses upgrade on new collisions."
2. **COR-010, "Lifecycle operations apply uniformly", item 3:** "**Update** — re-running the setup primitive reconciles installed state with the current version's spec."
   - **The change:** the setup primitive runs at the recorded versions. It moves no recorded version and runs no migration.
3. **COR-010, "Cross-tier upgrade requires explicit compatibility resolution":** "The reconciliation order — compatibility resolution → propagation → backbone migrations → component migrations → derivable-state reconciliation → recorded-version updates".
   - **The change:** a transition records its target before it writes anything and its completion last. The next transition finishes an incomplete one.
4. **COR-004, "Each command anchors to one mechanism or operation":** "A command performs one of: propagation, seed, merge, suspension management, validation, or read-only introspection." Also its rejected alternative, "One smart `update` verb that picks sync / merge / migration as needed."
   - **The change:** the list gains the version transition (question 1). The alternative is reworded to reject a verb that picks its operations by the state it finds.
   - **With it:** "Recovery from partial or broken state flows through `validate` plus targeted `sync` / `merge` instead" names upgrade for an incomplete transition.
5. **COR-048 point 1:** "It survives upgrade, sync, and uninstalling any capability or the tool itself, because none of them writes or removes it."
   - **The change:** none of them removes it, and an upgrade writes it only through the migrations point 5 names. Sync no longer writes it at all.
6. **ADR-049 point 1:** "the recovery is to **re-run** the reconcile / `upgrade`, which is idempotent (sync re-applies content, migrations detect already-applied state and no-op per COR-010, and the pin flip is a no-op once it matches)". Also its Implications on upgrade, "a mid-migration interruption is recovered by an idempotent re-run", and "A raise runs the *target* version's sync".
   - **The change:** refined in place. A re-run finishes the transition the manifest shows incomplete. The pin still flips last, with no two-phase commit.
7. **ADR-044 D1:** an unreachable release source "degrades loudly and continues with today's behaviour — sync the project from the current bundle".
   - **The change:** wording only. It continues with the transition to the current bundle's version. Its Implications and its amendment say the same.
8. **The decisions README, "The no-shared-files invariant":** "project-owned paths are never read or written by sync."
   - **The change:** sync never writes them. It reads the manifest. #1432 may make the same change first.

COR-001's "project-owned paths are not touched by sync" and its seeding cadence stay as written under the recommended answers to questions 5 and 8.

## Corrections to the reviews

The critic and the architect read the code on 10 October. Where this design's reading differs:

- **The adapters' recovery:** the architect expected adapters to recover by a per-component check. No adapter has a recorded version to check, and no adapter migration has ever run ("Where migrations strand").
- **Older code:** the architect's case for writing the target first rests on #1212's guard. It holds only from the release that ships #1212, since no released pkit has it.
- **A missing key:** the architect read a missing `migrated_version` as equal for sync. It reads as incomplete here. No project at the new release's content lacks it, and "equal" would let sync run over an interrupted first upgrade.
- **The replay:** both reviews rest it on idempotence. A replay also runs scripts on states that never needed them, so it needs a stronger contract and an audit, which found three scripts that can re-add a project's removals.
- **ADR-049:** the architect proposed partial supersession. Point 1's decision stands and only a fact was false, so the decisions README calls for a refinement in place. Its amendment is #1401's.
- **Seed recreation:** the architect leaned to keep it in sync. The maintainer's decision says sync writes no project-owned path, so question 8 recommends taking it out.
- **The migration order:** the architect put derivable state after every migration. One shipped migration reads a render made before the migrations ("Found on the way", 3).
- **Collision refusal:** the critic found it unbuilt. It is unbuilt in sync's refresh only. `pkit capabilities upgrade` has it.
- **The scripts:** seven backbone version directories hold eight scripts.

## Alternatives weighed

- **Sync runs at the recorded version by fetching it** (`run_bypassed` from sync). Not taken: a fetch at sync time is what ADR-033 rejected, the pin already routes every command, and offline it still stops.
- **Sync moves content but records no version.** Not taken: it breaks ADR-033's tie of content to code, and a capability's files would move without their migrations.
- **Skip per component without the backbone stop.** Taken inside a sync that proceeds. Without the backbone stop, a newer pkit would still copy its backbone files over older ones.
- **A ledger of migrations that ran.** Not taken: it drifts from the files and conflicts across branches, and COR-010 keys migrations on versions.
- **Pin at `pkit init`.** Not proposed: it reopens ADR-049 point 2 and puts every new project on the router's `uvx` path from its first command. It would make the unpinned stop rarer.
- **The deploy-only mode by default on a mismatch.** Not taken: a zero exit would let a pipeline hide the skew the stop exists to show.

## Slicing

A draft of the build issues, for filing after the maintainer decides. Each record is accepted before the work that cites it.

- **R1, [Docs] the core record and the refinements:** the new core record through the decision-author skill, partially superseding COR-017. COR-001, COR-004, COR-010 and COR-048 point 1 refined, and the decisions README's line. A `none` changeset, as #1431's.
  - **Shared with #1431 and #1432:** whichever lands first carries COR-001's principle and the change to COR-004's list, and the other adds its instance.
- **R2, [Docs] the realising ADR, by the architect:** with ADR-049 refined in place and ADR-044's wording. No changeset.
  - **After #1401,** which folds ADR-049's amendment, and in step with #1433, which refines ADR-049's rollback.
- **B1, [Task] sync never moves a version:**
  - the propagation step split from the sync command
  - the guard in both directions and on an incomplete transition, refusing under `--dry-run`, with a message per state
  - a capability copied at its recorded version only, others skipped and reported
  - no manifest write, no merge, no seed recreation, as questions 5 and 8 decide
  - `--force` accepted and ignored for one release
  - upgrade calls the step, and runs capability migrations where sync ran them, until B3
  - **Names #1435:** the shared guard. Whichever lands second depends on the first.
  - **Docs:** the CLI reference's `sync` entry, and the lifecycle README's "No path down". The changeset segment is question 7's.
- **B2, [Task] an upgrade records its target first and its completion last:**
  - the manifest key, written by init too, and the test that an older writer keeps it
  - the early return keyed on every recorded version
  - the backbone window from `migrated_version`
  - a missing manifest or a broken version seeded by upgrade, and the messages that named sync
  - the replay for a missing key, with its contract, its test and the audit
  - status showing an incomplete transition and pending components. **Names #1436 and #1440,** which extend status too
  - **Docs:** the lifecycle README's manifest format and upgrade flow
- **B3, [Task] every migration runs inside the transition, in order:**
  - capability migrations out of the refresh, after the copy, in dependency order
  - adapter migrations from the bundle, and adapter manifests written by init and by the transition
  - `pkit capabilities upgrade` as a transition of one component
  - the dependency check on the versions installed, after #1410
  - a new collision holds a capability back
  - the render a migration may read, per the ADR
  - **Docs:** the lifecycle README's upgrade flow and per-component upgrade
- **B4, [Task] the pinned flows:** the routed child finishes its own pin, offline included, and upgrade refuses under the router's fallback. **Names #1438,** which rewrites upgrade's and sync's messages too.
- **B5, [Task] capability install and upgrade use sync's guard,** if question 6 is answered yes.
- **B6, [Task] the recommended install is tagged,** as question 9 decides.
- **Later:** `--force` removed with a guidance migration, a release after B1.

**Order against the filed build:** #1410, then R1 and R2, then B1 to B6, then the conversion build from #1435 to #1444.

- **Why before #1435:** the conversion command, its status lines and its reports then build on settled sync and upgrade. #1435, #1438 and #1440 each depend on the B-issue that changes the same code.
- **If the conversion build goes first instead,** each pair's dependency reverses, as #1429's criterion allows.

## Found on the way

1. **Adapter migrations have never run in an adopter.** `install._install_adapter` copies no `migrations/`, and no code writes an adapter's per-component manifest. Taken by B3.
2. **`install._install_adapter` never copies `permission-enforcement.yaml` either.** `permissions.py` reads it from the project, so in an adopter the line naming dimensions no native layer enforces is always empty.
3. **The two `1.150.0/` migrations interfere, by reading the code.** Sync renders `.pkit/.gitignore` before the migrations, while no `process` block exists, so the render ignores the journals.
   - `keep-process-journal-logging` runs first and writes `committed: true` for a project that tracks its journals.
   - `untrack-runtime-ignored-files` then reads the earlier render and stages the removal of those journals from the index.
   - **Before the next release:** worth an issue of its own. Each script's test runs it alone.
4. **The next release ships the two `1.150.0/` migrations, and a sync strands them** for an unpinned project, until B1 lands. The journal one matters: logging stops silently. Its changelog could say to run `pkit upgrade`, not `pkit sync`.
5. **#1212 is unreleased.** Every released pkit writes its older content over a newer project. The protection this design leans on starts with the next release.
6. **Upgrade under the router's fallback raises the pin to the installed version,** against ADR-049 point 5. Taken by B4.
7. **A pinned project whose installed pkit equals its pin** runs `pkit upgrade` as itself, not as the routed child. Without a terminal it reports "Already at backbone" and does not advance, while ADR-049 point 5 says a pinned upgrade advances with no `uv` step.
8. **COR-048 point 1 says an upgrade never writes the configuration file.** Point 5 lets an upgrade migration write it, and `1.150.0/001-keep-process-journal-logging` and project-management's `0.55.0/004` do.
9. **COR-010's Context says COR-004 "names the upgrade command".** COR-004 names no upgrade.
10. **The CLI reference's `upgrade` entry has two stale lines.** It says migrations run "then runs `sync`", while the code runs sync first. It says an unpinned upgrade writes "no pin file", while upgrade pins by default.
11. **`_sync_installed_capabilities` treats an externally-sourced registration as kit-shipped.** It refreshes it from the bundle when the methodology ships a capability of that name, and reports it orphaned otherwise.
12. **A capability refresh with an unreadable installed version runs every shipped migration,** project-management's `0.54.0/001` among them, which grandfathers a bootstrap that may never have happened. Taken by B1, where sync runs no migration, and B3, where upgrade holds such a capability back.
13. **The lifecycle README says "a corrupt `backbone_version` is one sync repairs".** Sync repairs it by recording the running pkit's version, whatever the files hold.
14. **Read-only commands under another release stay silent.** `pkit validate` with a newer pkit judges older content by newer rules. #1436 reports that mismatch in status and validation.
