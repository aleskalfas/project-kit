---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/migrations.py
        - src/project_kit/scaffolds.py
        - src/project_kit/visibility.py
        - src/project_kit/upgrade.py
        - src/project_kit/default_branch.py
      record: [COR-010, COR-059, "COR-048#5", "COR-050#12", "COR-050#14", "COR-054#3", "ADR-065#14"]
      artefact:
        - .pkit/lifecycle/manifest.md#how-a-registered-command-is-run
        - .pkit/lifecycle/manifest.md#backbone-manifest-projectpkitmanifestyaml
---

# Migration framework

How a migration carries an installed project's state across a version transition, and what each migration script must keep ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)).

## Contents

<!-- pkit:contents -->
- [What ships a migration](#what-ships-a-migration)
- [Directory layout](#directory-layout)
- [Naming](#naming)
- [Which version a migration targets](#which-version-a-migration-targets)
- [Three scopes (per tier)](#three-scopes-per-tier)
- [Script contract](#script-contract)
- [Tier independence](#tier-independence)
<!-- /pkit:contents -->

## What ships a migration

A change that alters an installed project's state observably, and breaks against it, ships a migration in the same change ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)). The change ships the migration at the tier whose state it alters.

- **Ships one:**
  - a file or directory renamed or removed in a tree the methodology ships
  - a `schema_version` bump in a YAML schema whose shape changes incompatibly
  - a breaking change to a `pkit` command's signature
  - a capability's subtree restructured
- **Ships none:**
  - a pure addition, such as a new skill, schema, record or component
  - a documentation refinement, an internal refactor or a behaviour-preserving fix
  - a section's heading renamed or removed in a document the methodology or a component ships. A project that receives the document cannot anchor its sections, since a synced tree is never a place (COR-050 point 14). Where the document is authored, the change mends the anchors on the heading, as validation requires (COR-050 point 12).

A heading a component requires in a project's own documents is part of the component's contract, so the last case does not cover it. Whether a change to it ships a migration is decided as for any other change.

`pkit migrations check-diff` fails these changes:

- a change whose renames or removals no migration covers
- a change that adds a migration at a version already released ("Which version a migration targets", below)
- a change that adds one with a number its folder already holds ("Naming", below)

The check leaves decision records out, so a renamed or removed record passes it.

## Directory layout

Backbone migrations live in a kit-wide location:

```
.pkit/migrations/backbone/<major>.<minor>.0/<NNN>-<slug>.sh
```

Component migrations live within the component:

```
.pkit/capabilities/<capability>/migrations/<major>.<minor>.0/<NNN>-<slug>.sh
.pkit/adapters/<adapter>/migrations/<major>.<minor>.0/<NNN>-<slug>.sh
```

## Naming

A migration script is named `<NNN>-<slug>.sh`, such as `001-add-status-labels.sh`. `NNN` is a zero-padded execution-order index within the directory, and `<slug>` is a kebab-case description.

Each number is used once in a folder. The runner runs a folder's scripts in the order of their names. So two scripts of one number would run in the order their slugs give.

- **The stamp.** `pkit new migration` numbers a script one past the highest in its folder, in the working tree or on the default branch.
- **The check.** `pkit migrations check-diff` fails a script a change adds, or moves in, whose number another script in its folder holds. It reads the folder as merging the base would leave it. So a number another change took on the base since the branch left it counts too. It skips a script the project receives by sync.
  - **The finding:** it gives each script it names a number of its own to take, past the highest in the folder. Of two scripts the change itself adds with one number, it names the one whose name sorts later.
- **Renumbering.** The stamp reads no scope. So a script that must run before one already in its folder, such as a manifest-schema script beside a resource-scoped one, is renumbered by hand. That script takes the lower number, and the other moves up. Renumber only in a folder no release has shipped.
  - **Unchecked:** no check holds this, since a rename inside a migrations folder triggers nothing.

## Which version a migration targets

A migration's folder names the version it carries a project to, never one already released. The runner runs a folder only past the version a project records ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)). So a folder at or below a released minor never runs for a project already there, and nothing else reports it.

- **The stamp.** `pkit new migration` without `--version` takes the highest of these:
  - the next minor past the version the default branch records for the tier:
    - `.pkit/VERSION` <!-- unanchored: names the file the step reads or writes, not its content --> for the backbone
    - the component's `package.yaml` for an adapter or a capability
  - the version the working tree records, where it is above that one, as on the branch of a project whose change bumps its own version
  - the next major, where its folder already waits, so the script runs after the migrations of the change that made it

  It joins no folder further ahead. It reads the default branch from git objects, as a command that allocates from settled state does ([COR-054](../decisions/core/COR-054-default-branch.md) point 3). It refuses a `--version` at or below the default branch's version, and names the version to give.
- **The check.** `pkit migrations check-diff` fails a script a change adds, or moves in, whose folder is at or below the version its tier records at the base's tip. It reads the tip, not the branch point. A tier the tip records no version for, such as a new component, has nothing released.
  - **What it skips:**
    - a script the project receives by sync
    - one the tip already holds, at its path or under another name in its folder with the same content, as a rename leaves it
- **What neither predicts.** Neither reads pending changesets for a major: the release computes the version, by the project's version-bump policy. A folder that names a minor below the release still runs inside the transition across it, since the runner's window is a range of minors.

## Three scopes (per tier)

Each tier's migrations fall into three scopes:

- **Manifest-schema migrations** bridge a manifest format change. They run *first* in any upgrade flow that touches them. Each manifest (backbone, per-component) has its own schema. Bumping either may need its schema migrated.
- **Structural migrations** affect the directory shape of the tier (a kit-wide rename in the backbone, or a capability's internal restructure within the capability). They run *before* resource-scoped migrations of the same target version.
- **Resource-scoped migrations** affect a single resource type (a label is renamed, a setting key changes shape, a primitive moves).

Within a single `<major>.<minor>.0/` directory, the numbers carry this order ("Naming", above). Manifest-schema scripts take the lowest, structural scripts take the next, and resource-scoped scripts take the highest.

## Script contract

Each migration script:

- Is **versioned** by its directory (the `<major>.<minor>.0/` it lives in).
- Is **idempotent** — re-running a completed migration is a no-op. Migrations should detect already-applied state and exit cleanly.
- **Is safe over any state, if it is a backbone migration.** It acts only on a positive sign that its change is needed, and never deletes by a path's name or position alone. A version transition may run every backbone migration again over a project whose migration history is unknown (COR-059). A missing default the migration adds counts as a positive sign. So running it again may restore a default the project removed after it first ran, and the release's notes say so.
- Receives `ROOT` (project root) in the environment.
- **Calls `pkit` by its bare name, and reaches the running pkit, the one that runs its transition.** The migration runner puts a `pkit` of its own first on the script's `PATH`, and every process that inherits that `PATH` finds the same `pkit`. That `pkit` runs the running pkit's code under the same interpreter, and never enters the router. So neither the pin nor the operator's `PATH` decides which release answers. The version of that `pkit` is the `backbone_version` the manifest records while the migrations run.
  - **Where that `pkit` lies:** in a fresh folder of its own inside `.pkit/.migration-runner/`, made for each set of scripts the runner runs, the backbone's, an adapter's or a capability's. Before the first script, step 3 of a transition writes the folder's ignore entry into `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content -->. Each folder is removed on every exit, and `.pkit/.migration-runner/` too once it is empty. No run reuses a folder that a killed run left behind, and such a folder is safe to delete.
  - **When that `pkit` cannot run:** before the first script, the migration runner asks its `pkit` for its version.
    - **The temporary folder:** the runner makes its folder in the system's temporary folder, and asks again, where the folder in the project cannot be made or written. It does the same where the runner's `pkit` answers with another version or not at all. It does the same where `.pkit/.migration-runner/` is a link or a folder another user owns or can write. It does the same where a bare `pkit` finds another `pkit` before the runner's.
    - **When that fails too:** the transition stops before the set's first script, as a failing migration does. The message names both folders, and `TMPDIR`, which chooses where the temporary folder lies. A folder that forbids running files is the usual cause.
  - **No check needed:** a `command -v pkit` check always passes inside a transition. A script may keep one for a run outside a transition, by hand or in a test.
  - **No routing variable:** the script sets no variable that stops the router, `PKIT_NO_ROUTE` or `PKIT_ROUTED`. Commands read them too, not only the router, so one would change what a command does.
  - **Nothing from where `pkit` lives:** the migration runner's `pkit` lies in a folder of its own beside no install, and is gone after the run.
  - **What it reads:** what the backbone computes, about content alone: the release's and the project's own. The script reads it through the reading commands ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run), "The seams back"). It applies the answer itself.
    - **Never a recorded version or the completion,** as `status` shows them. While the migrations run, `backbone_version` already names the target, and `completed_version` does not name it yet ([`manifest.md`, "Backbone manifest (`<project>/.pkit/manifest.yaml`)"](manifest.md#backbone-manifest-projectpkitmanifestyaml)). A component's manifest names its old version until its own migrations end. An answer built on a recorded version or the completion mixes two releases.
    - **Which components are installed** does not move while the migrations run, so a check of it is sound. `capabilities project-rule-set` makes one before it answers.
  - **What it never runs:** a command that propagates, seeds or merges, moves a recorded version, writes the pin, or changes which components are installed.
    - **Such commands:** `init`, `sync`, `upgrade`, `pin`, `unpin`, `merge`, `agents adopt`, `agents reconcile --write`, and `capabilities install`, `upgrade`, `register` and `uninstall`.
    - **They refuse:** the migration runner sets `PKIT_MIGRATION=1` in the script's environment, and every process the script starts inherits it. Each such command checks it first, before it reads or writes anything, and under `--dry-run` too. Any value but an empty one refuses the command, and nothing overrides the refusal. So a script that runs one fails, and stops the transition.
    - **`upgrade`:** it refuses before it looks for a project, so it updates no tool either.
    - **The marker is the runner's:** the script never sets or unsets `PKIT_MIGRATION`. The router never reads it. It is no routing variable, since a command reads it only to refuse.
    - **Allowed:** the reading commands, and `config set` for a key whose owning record specifies the migration that writes it (COR-048 point 5).
- Uses `set -euo pipefail`. The runner runs each script with `bash`.
- **Updates the affected resource.** For resources whose state lives in a manifest (component registry entries, opaque backend IDs), the migration updates the manifest entry. For derivable resources (files, labels, symlinks), no manifest update is needed. The transition regenerates them from the new kit-side spec at the new version.

## Tier independence

Component migrations are tied to the component's version, not the backbone's. A capability upgrade `0.11.0 → 0.12.0` runs the capability's `0.12.0/` migrations regardless of which backbone version is current — subject to compatibility constraints checked at upgrade entry.
