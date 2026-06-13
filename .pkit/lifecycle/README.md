---
variant: specialized
---

# Lifecycle

How project-kit installs, updates, and removes resources — and how versions evolve across the backbone and its components.

The architecture lives here. The rules and rationale (why two tiers, why per-component manifests, why migrations split by scope and tier) live in `.pkit/decisions/core/COR-010-resource-lifecycle.md`. This document is the spec: manifest schema, upgrade procedure, migration layout, register/unregister mechanics, version-resolution semantics, and worked examples.

Paths and exact YAML shapes are illustrative — the install/sync runtime (per the build roadmap + COR-004) settles them. The shapes here are what every other area of the kit can rely on once the runtime ships.

Developers don't stamp these layouts by hand. The kit ships authoring commands (`pkit new adapter <name>`, `pkit new capability <name>`, `pkit new migration [...]` — specified in `.pkit/cli/README.md` and grounded in COR-005 + COR-017) that scaffold the contract this document defines. Templates for the manifest skeletons and migration scripts live in `.pkit/lifecycle/templates/` so a kit upgrade that changes a contract also updates what gets stamped.

## Layout

```
.pkit/
├── manifest.yaml                                    ← backbone manifest (recorded version + component registry)
├── migrations/
│   └── backbone/
│       └── <major>.<minor>.0/
│           ├── 001-<slug>.sh
│           └── ...
├── capabilities/<capability>/
│   ├── package.yaml                                 ← component metadata: version, requires_backbone
│   ├── migrations/<major>.<minor>.0/...
│   └── project/
│       └── manifest.yaml                            ← per-component manifest
└── adapters/<adapter>/
    ├── package.yaml
    ├── migrations/<major>.<minor>.0/...
    └── project/
        └── manifest.yaml                            ← per-component manifest
```

## The two tiers

**Backbone** — the cohesive core that ships together: decisions (CORs and the spec), rules, the CLI / runtime. One coordinated release, one version number.

**Components** — installable, independently-versioned pieces that depend on a backbone version range. Capabilities (`project-management`, `evidence` today; per COR-017) and adapters (`claude-code` today; future `codex` / `cursor` / etc.) are components. Each component declares a semver range of compatible backbone versions in its `package.yaml`. (Per COR-027, the bundle pattern was retired — alternative implementations within a capability live as capability-internal data, not as filesystem-level bundles.)

Both tiers use semantic versioning (`major.minor.patch`). Components express compatibility via `requires_backbone: ">=X.Y.Z, <W.0.0"`. Patch-level releases are backward-compatible bug fixes and have no migrations — migration directories are named with the full three-segment target version, with patch always `0` (e.g., `2.1.0/`), and cover all patches within that minor line.

See COR-010 for the rationale.

## Manifest schema

### Backbone manifest (`<project>/.pkit/manifest.yaml`)

```yaml
schema_version: 1
backbone_version: 2.1.0

# Component registry — paths to per-component manifests.
components:
  - kind: capability
    name: project-management
    manifest: .pkit/capabilities/project-management/manifest.yaml
  - kind: adapter
    name: claude-code
    manifest: .pkit/adapters/claude-code/project/manifest.yaml
```

Small by design. No component data is duplicated here — that lives in each component's manifest. The backbone manifest carries:

- **`schema_version`** — version of *this* manifest's own schema, independent of any component's. Bumping it triggers a backbone manifest-schema migration.
- **`backbone_version`** — the recorded backbone version this project is at.
- **`components`** — the registry. Each entry is a `{kind, name, manifest}` triple pointing at a per-component manifest file.

### Per-component manifest (one per installed component)

```yaml
schema_version: 1
component:
  kind: capability          # or 'adapter'
  name: project-management
  version: 0.12.0
  installed_at: 2026-04-15T12:00:00Z

requires_backbone: ">=1.0.0,<2.0.0"

backend_state:
  project_board:
    uuid: PVT_kwDOAA12345
    name: adopter-kit
```

Sections:

- **`schema_version`** — version of *this* component-manifest schema. Bumping it triggers a component manifest-schema migration.
- **`component`** — kind, name, recorded version, install timestamp.
- **`requires_backbone`** — semver range pinned to this version of the component. Recorded into the manifest at install/upgrade so the next upgrade run can verify compatibility.
- **`backend_state`** — opaque backend identifiers the kit cannot rederive (board UUIDs, webhook IDs, etc.). Empty `{}` for components that have none.

Notably absent: enumerations of files, labels, symlinks, settings entries, templates. These are *derivable* state — the kit-side spec at the component's recorded version + the adopter's config tells you what should exist; the validate/upgrade reconciliation tells you whether reality matches.

## The component registry

The backbone manifest's `components` list is the canonical install record.

**Install** a component → create its per-component manifest at the designated path, then append a `{kind, name, manifest}` entry to `components`.

**Remove** a component → delete the registry entry, then delete the per-component manifest file. Adopter-owned content authored on top of the component (project-side records, customisations) is left untouched per COR-005 and the no-shared-files invariant.

**Status / validate / upgrade** walk the registry to find component manifests, then operate per component.

## Migration framework

### Directory layout

Backbone migrations live in a kit-wide location:

```
.pkit/migrations/backbone/<major>.<minor>.0/<NNN>-<slug>.sh
```

Component migrations live within the component:

```
.pkit/capabilities/<capability>/migrations/<major>.<minor>.0/<NNN>-<slug>.sh
.pkit/adapters/<adapter>/migrations/<major>.<minor>.0/<NNN>-<slug>.sh
```

### Naming

`<NNN>-<slug>.sh`, where `NNN` is a zero-padded execution-order index within the directory and `<slug>` is a kebab-case description (e.g., `001-add-status-labels.sh`).

### Three scopes (per tier)

**Manifest-schema migrations** bridge a manifest format change. They run *first* in any upgrade flow that touches them — the runtime needs to read the manifest correctly before tracking subsequent migrations. Each manifest (backbone, per-component) has its own schema; bumping either may need its schema migrated.

**Structural migrations** affect the directory shape of the tier (a kit-wide rename in the backbone; a capability's internal restructure within the capability). They run *before* resource-scoped migrations of the same target version.

**Resource-scoped migrations** affect a single resource type (a label is renamed, a setting key changes shape, a primitive moves).

Within a single `<major>.<minor>.0/` directory, scope ordering is: manifest-schema → structural → resource-scoped, by `NNN` index within each scope.

### Script contract

Each migration script:

- Is **versioned** by its directory (the `<major>.<minor>.0/` it lives in).
- Is **idempotent** — re-running a completed migration is a no-op. Migrations should detect already-applied state and exit cleanly.
- Receives `ROOT` (project root) in the environment.
- Uses `set -euo pipefail` (or the equivalent for whatever shell/language the runtime supports — settled by the build roadmap).
- **Updates the affected resource.** For resources whose state lives in a manifest (component registry entries, opaque backend IDs), the migration updates the manifest entry. For derivable resources (files, labels, symlinks), no manifest update is needed — the upgrade flow's reconciliation step regenerates them from the new kit-side spec at the new version.

### Tier independence

Component migrations are tied to the component's version, not the backbone's. A capability upgrade `0.11.0 → 0.12.0` runs the capability's `0.12.0/` migrations regardless of which backbone version is current — subject to compatibility constraints checked at upgrade entry.

## The upgrade flow

The upgrade command transitions an adopter project to a target backbone version (and optionally specific component versions). Six steps:

1. **Resolve compatibility.** Read each installed component's `requires_backbone` against the target backbone version. Refuse to upgrade backbone past a component's range, unless the component is also being upgraded to a version compatible with the new backbone. Surface conflicts so the adopter can address them (upgrade specific components, pin backbone, or remove an incompatible component).
2. **Pull new propagated content.** Run sync (per COR-001) for the backbone. Component-side propagated content updates as part of each component's upgrade.
3. **Run backbone migrations** in order: manifest-schema → structural → resource-scoped, across minor-version boundaries from current to target.
4. **For each component being upgraded**, run its migrations in version order with the same scope ordering within each `<major>.<minor>.0/` directory.
5. **Reconcile derivable state.** Each component's setup primitive re-applies the kit-side spec at its current version + adopter's config (idempotent — labels, files, symlinks, merged settings).
6. **Update recorded versions.** Backbone version in the backbone manifest; component versions in their respective manifests.

Idempotent: running upgrade on a current adopter is a no-op.

### Per-component upgrade

Upgrading just one component (e.g., the project-management capability) skips backbone-side steps as long as the component's new version remains within `requires_backbone` of the current backbone. The same compatibility check from step 1 gates entry. Steps 4 (component migrations), 5 (component-scoped reconciliation), and 6 (component manifest version bump) run; step 2 pulls only the component's source.

## Reconciling derivable state

Two commands consume the manifests differently for the same conceptual job — "is reality consistent with the spec at the recorded version?":

- **`validate`** computes the expected state for derivable resources at each recorded version + adopter's config, compares to actual reality, reports drift. Manifest-tracked resources are compared directly: manifest entries vs. backend.
- **`upgrade`** does the same comparison, then *applies* changes to bring reality into line (step 5 of the flow).

Either way, the kit-side spec at the recorded version is the source of truth for what should exist; the manifest tracks only what the spec can't recover (recorded version, opaque IDs).

## Worked example

A full worked example demonstrating the upgrade flow across backbone + components is deferred for a focused rewrite. The prior example was built around the now-retired bundle pattern (per [COR-027](../decisions/core/COR-027-alternative-impls-as-capability-data.md)); rewriting it against the capability + adapter shape is queued.

For concrete examples of the contract this document defines, see:

- The kit's own `.pkit/manifest.yaml` for the backbone-manifest shape with one capability + one adapter entry.
- `.pkit/migrations/backbone/<X.Y.0>/` for backbone migration script structure.
- `.pkit/capabilities/project-management/migrations/0.12.0/` for a capability-tier migration that handles file-rename + adopter-state cleanup.
- `.pkit/adapters/claude-code/migrations/` for adapter-tier migration patterns.
