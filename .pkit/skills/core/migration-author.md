---
name: migration-author
description: Author a new migration script (backbone, adapter, or capability tier) per the COR-010 contract. Use when a version bump needs to bridge installed projects' state to the new version.
metadata:
  wraps_command: pkit new migration
gates:
  - COR-005
  - COR-008
  - COR-010
  - COR-017
reads:
  records:
    - COR-027
  paths:
    - .pkit/cli/README.md
    - .pkit/lifecycle/README.md
    - .pkit/decisions/README.md
    - .pkit/VERSION
---

# Authoring a migration

This skill walks through adding a new **migration script** per COR-010's lifecycle contract. A migration bridges installed projects' state across a version transition — adding labels, renaming files, restructuring manifests, etc. Migrations are versioned (tied to a `<major>.<minor>.0/` directory), idempotent (safe to re-run), and scoped to one tier (backbone, adapter, or capability).

## Acceptance gate (run first)

Per `.pkit/decisions/README.md`'s acceptance gate: verify every record in `gates:` is `accepted` before authoring. Halt if any is `proposed` or `superseded`.

The current dependencies:

- **COR-005** — the adapter pattern; an adapter owns its migration tree. Its bundle half is retired (COR-027).
- **COR-008** — git workflow conventions; the commit step.
- **COR-010** — resource lifecycle; fixes the migration framework (tiers, scopes, directory layout, idempotence contract).
- **COR-017** — the capability pattern; a capability owns its migration tree.

## Procedure

### 1. Pick the tier

The migration lives in one of three trees, picked by the resource it affects:

- **`backbone`** — the migration affects backbone-level state (decision records, rules, the CLI surface, backbone-wide directory shapes). Lives under `.pkit/migrations/backbone/<X.Y.0>/`.
- **`adapter`** — the migration affects one specific adapter's state (settings, deployed paths, hooks for that harness). Lives under `.pkit/adapters/<name>/migrations/<X.Y.0>/`.
- **`capability`** — the migration affects one specific capability's state (its project-side files, labels, templates, configuration). Lives under `.pkit/capabilities/<name>/migrations/<X.Y.0>/`.

Pick the most specific tier that covers the change. A capability's internal change → capability tier (not backbone), even if the change is conceptually "across the methodology's capabilities".

### 2. Pick the scope

Each tier has three scopes that determine the script's role and execution order within a version's directory (per COR-010 / `.pkit/lifecycle/README.md`'s "Three scopes per tier"):

- **`manifest-schema`** — bridges a manifest format change. Runs **first** in any upgrade flow that needs it, before any structural or resource-scoped migration of the same target version.
- **`structural`** — affects the tier's directory shape (a backbone-wide rename; a capability's internal restructure within the capability). Runs **before** resource-scoped migrations of the same target version.
- **`resource`** — affects one specific resource (a label, a setting key, a template). The most common scope.

### 3. Pick the target version

The target version is the `<major>.<minor>.0` the migration applies *up to*. It is the version that the migration's backbone or component takes in the release that ships the change. Per COR-010, patches have no migrations — the patch segment is always `.0`, and one minor-version directory covers all patches within that line. So that release raises that version by at least a minor.

It is never a version already released. A project already at that version never runs the script. The stamp and `pkit migrations check-diff` both refuse it (the lifecycle spec's "Which version a migration targets").

How that version is known depends on the project's version-bump policy, which COR-010 defers to. Read the project's own record of it first. Two common shapes:

- **Where the change's own branch bumps the version,** the target is the bumped version. The stamp picks it without `--version`, from `.pkit/VERSION` or the component's `package.yaml` after the bump.
- **Where a release step bumps the version after the change merges,** the branch carries a version already shipped. The target is the backbone's or component's version in the next release. Without `--version`, the stamp picks the next minor past the version the default branch records, or the next major where its folder already waits. Where the release will be a major and no folder waits yet, pass it. Check the version again just before the change merges: `pkit migrations check-diff` fails a script whose version a release took meanwhile.

### 4. Pick the slug

Kebab-case, 2–4 words, describing what the migration does. Examples: `add-status-labels`, `rename-chore-to-maintenance`, `manifest-schema-v2`, `decisions-frontmatter-author`.

### 5. Stamp the scaffold

Use the authoring command (per `.pkit/cli/README.md`):

```
pkit new migration --tier <tier> [--component <name>] [--version <X.Y.0>] --name <slug> [--scope <scope>]
```

- `--tier` is required.
- `--component` is required when `--tier` is `adapter` or `capability`.
- `--version` defaults to the next version past the one the default branch records for the tier: `.pkit/VERSION` for the backbone, a component's `package.yaml` `version` field for a component. The command prints the version it picked and why. Pass step 3's target explicitly when it differs. A version at or below the default branch's is refused, and the refusal names the version to give.
- `--name` is the slug, required.
- `--scope` defaults to `resource`. Set to `manifest-schema` or `structural` per step 2.

The command stamps `<NNN>-<slug>.sh` in the right `<X.Y.0>/` directory, where `NNN` is the next zero-padded index in that directory, past the default branch's scripts there too. The script is made executable and includes the COR-010 contract boilerplate (`set -euo pipefail`, `ROOT` env consumption, idempotence pattern).

### 6. Implement the migration

Open the stamped script and replace the TODO body with the actual change. Four requirements (per COR-010 / lifecycle spec's "Script contract"):

- **Idempotent** — detect already-applied state and exit cleanly. The stamped boilerplate shows the pattern:

  ```bash
  if <state is already correct>; then
      echo "  exists  <description>"
      exit 0
  fi
  # ... apply ...
  ```

- **Safe over any state, for a backbone migration** — it acts only on a positive sign that its change is needed, and never deletes by a path's name or position alone. A version transition may run every backbone migration again over a project whose migration history is unknown. A missing default the migration adds counts as a positive sign. So running it again may restore a default the project removed after it first ran. If the script adds a missing default, say so in the release's notes.

- **Updates the affected resource.** For derivable resources (files in the core content directory, labels on a tracker), the migration mutates the resource directly — no manifest update. For non-derivable resources (opaque backend IDs in `backend_state`), the migration updates the manifest entry.

- **Calls `pkit` by its bare name, where it runs one.** It reaches the running pkit, the one that runs the transition. The migration runner puts a `pkit` first on the script's `PATH` that runs the running pkit's code and never enters the router. So neither the pin nor the operator's `PATH` decides which release answers.
  - Set no variable that stops the router, `PKIT_NO_ROUTE` or `PKIT_ROUTED`. Commands read them too, so one would change what they do.
  - Derive nothing from where `pkit` lives. The runner's `pkit` lies in a folder of its own, gone after the run.
  - Need no `command -v pkit` check: inside a transition it always passes. A script may keep one for a run outside a transition, by hand or in a test.
  - Ask the backbone about content alone, the release's and the project's own, through its reading commands, and apply the answer in the script. Never ask about a recorded version or the completion, as `pkit status` shows them: while the migrations run, they belong to two releases. A check that a component is installed is sound.
  - Never run a command that propagates, seeds or merges, moves a recorded version, writes the pin, or changes which components are installed. Examples are `sync`, `upgrade`, `pin` and `capabilities install`, and the lifecycle spec's "Script contract" lists them all. Each refuses while `PKIT_MIGRATION` is set, which the runner sets for every script, so a script that runs one stops the transition. Never set or unset that marker.

Use only the dependencies the project ships with — `bash`, standard UNIX tools, `pkit`, `python3` with its standard library only, `git`, `gh`, `yq` if YAML manipulation is needed.

### 7. Self-check

Walk the script against the contract:

- *Does it `set -euo pipefail`?*
- *Does it consume `ROOT` from the environment, not hardcode paths?*
- *Is it idempotent — would re-running on already-migrated state be a no-op?*
- *For a backbone migration: does it act only on a positive sign that its change is needed, and never delete by a path's name or position alone?*
- *Does it update the affected resource (or the relevant manifest entry, for non-derivable state)?*
- *Does each `pkit` call use the bare name, with no routing variable and nothing taken from where `pkit` lives? Does it ask about content alone, never a recorded version or the completion? Does it run no command the "Script contract" rules out, and leave `PKIT_MIGRATION` as the runner set it?*
- *Did you place it in the right tier × version × scope ordering?*

Test the script locally if practical: on a fresh checkout and, for a backbone migration, on a state that never needed it and on one the project changed after it first ran. Run by hand, a script's bare `pkit` is the shell's, routed by the project's pin if it has one. For such a run, put first on the `PATH` a `pkit` of the release that ships the migration, and set `PKIT_MIGRATION=1`, so a command the contract rules out refuses as it would in a transition.

### 8. Commit

Per COR-008, conventional-commits format. Type is typically `feat` (a new migration is new behaviour at the target version); scope is the tier (or the component's name for an adapter or capability migration):

```
feat(<scope>): add migration <X.Y.0>/<slug>

<body — 1–3 paragraphs explaining what state the migration bridges, what
the new version expects, and any caveats for adopters>
```

The migration lands in the same change-set as the surface change it bridges, per COR-010. So does the version bump, in the form the project's version-bump policy gives it.

## Variations

- **A migration that fully reconciles is unnecessary** — if the transition regenerates the resource from the new spec, no migration is needed. Migrations only exist for state the transition cannot derive (renames, removals, opaque backend IDs).
- **Multiple migrations at one version** — the next-index numbering supports this. Place manifest-schema migrations first (lowest NNN), then structural, then resource-scoped. The runtime walks them in that order.
