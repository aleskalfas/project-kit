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
│   ├── package.yaml                                 ← component metadata: version, requires_backbone, requires_capabilities
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
  - kind: capability
    name: homegrown
    origin: incubated-in-repo                         ← in-repo (incubated) capability (COR-031)
    manifest: .pkit/capabilities/homegrown/manifest.yaml
  - kind: adapter
    name: claude-code
    manifest: .pkit/adapters/claude-code/project/manifest.yaml
```

Small by design. No component data is duplicated here — that lives in each component's manifest. The backbone manifest carries:

- **`schema_version`** — version of *this* manifest's own schema, independent of any component's. Bumping it triggers a backbone manifest-schema migration.
- **`backbone_version`** — the recorded backbone version this project is at.
- **`components`** — the registry. Each entry is a `{kind, name, manifest}` triple pointing at a per-component manifest file, optionally carrying an **`origin`** marker (below).

#### Capability origin (COR-031)

A capability-kind registry entry may carry an **`origin`** field recording where the capability came from — the property the lifecycle keys off to decide what `sync` / `upgrade` may do to it:

- **`kit-shipped`** (the default) — the capability ships in the kit source and was copied into the adopter on `capabilities install`. This is the status quo COR-017 describes. **The field is omitted when it holds this default**: an absent `origin` reads as `kit-shipped`, so every registration written before this field existed keeps its behaviour with no re-tagging (the change is purely additive — no migration; COR-031 D2).
- **`incubated-in-repo`** — the capability was authored in the adopter's *own* repo and registered in place via `capabilities register` (no copy). Its subtree is adopter-owned content, not a copy of anything the kit ships.

Origin lives **here, in lifecycle-owned install-state — never inside the capability's own subtree.** An incubated capability's subtree (including its authored `package.yaml`) is entirely adopter-owned; writing lifecycle state into it would re-create the ownership blur the origin distinction exists to prevent (COR-031 D2). For an incubated capability, no kit-written per-component `manifest.yaml` is stamped at all — its version of record is its authored `package.yaml`, and dependency gating reads from there.

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

### Per-capability `package.yaml` (source-side metadata)

A capability's source-side `package.yaml` carries the metadata the lifecycle reads at install and upgrade time. Adapters have a similar shape.

```yaml
schema_version: 1
component:
  kind: capability
  name: evidence
  version: 0.5.1
description: "Citation discipline — ..."
requires_backbone: ">=1.26.0,<2.0.0"

# Optional: declared dependencies on other capabilities (COR-030).
# Each entry is a capability name + semver range for the installed version.
# Absence of this field (or an empty list) means no dependencies.
requires_capabilities:
  - name: project-management
    version: ">=0.20.0,<1.0.0"

# Optional: this component's git-footprint paths outside `.pkit/` (ADR-009).
# `pkit visibility private` routes these into `.git/info/exclude`.
footprint:
  - .claude/skills

# Optional: this component's runtime-local files to git-ignore (ADR-009
# Amendment 1). Aggregated into the pkit-owned `.pkit/.gitignore`.
runtime_ignore:
  - .pkit/capabilities/<name>/project/some-runtime.log
```

Fields:

- **`requires_backbone`** — semver range of backbone versions this capability version is compatible with. Evaluated at install and upgrade.
- **`requires_capabilities`** — optional list of capability dependencies, each a `{name, version}` pair where `version` is a semver range. The lifecycle gates on these at install, upgrade, and uninstall (COR-030). Absence means no dependencies; capabilities without this field are unaffected.
- **`footprint`** — optional list of git-footprint globs this component deploys outside `.pkit/` (e.g. an adapter's `.claude/` deploys). Aggregated across installed components and routed into the per-clone `.git/info/exclude` by `pkit visibility private` (ADR-009). Absence means the component adds nothing to the footprint beyond the backbone's own `.pkit/`.
- **`runtime_ignore`** — optional list of runtime-local file globs this component wants git-ignored (e.g. per-clone logs, caches, sidecars under the component's own subtree). Aggregated across installed components and wholesale-rendered into the pkit-owned `.pkit/.gitignore` (ADR-009 Amendment 1). Each component names only paths it owns — core never invents adapter/capability paths. Absence means the component contributes no runtime-ignore lines; the backbone and the propagated permissions surface (which have no `package.yaml`) declare theirs through a core-level seam instead.

## The component registry

The backbone manifest's `components` list is the canonical install record.

**Install** a component → run the pre-flight checks (see below), create its per-component manifest at the designated path, then append a `{kind, name, manifest}` entry to `components`.

**Register an in-repo (incubated) capability** (COR-031) → a no-copy variant of install for a capability the adopter authored in its own repo. Run the same pre-flights *except* "exists in kit source" (the in-repo tree *is* the source), then append a `{kind, name, origin: incubated-in-repo, manifest}` entry — **no subtree copy, and no kit-written per-component manifest** (the tree is adopter-owned; COR-031 D2/D3). Deploy primitives and dependency gating run identically to install (COR-031 D1) — only source-reconciliation differs (below).

**Remove** a component → run refusal checks (see below), delete the registry entry, then delete the per-component manifest file. Adopter-owned content authored on top of the component (project-side records, customisations) is left untouched per COR-005 and the no-shared-files invariant. For a **capability**, whether the capability's *subtree* is also deleted is origin-dependent — a kit-shipped copy is deleted, an incubated (adopter-authored) subtree is kept unless explicitly purged (COR-031 D4; see "Uninstall: origin-aware removal" below).

**Status / validate / upgrade** walk the registry to find component manifests, then operate per component.

### Install pre-flight checks

Before placing files, `pkit capabilities install` runs four checks in order:

1. **Already installed?** Refuse with a hint to use `upgrade`.
2. **Backbone compatibility** — the capability's `requires_backbone` range must include the current backbone version. This is the shared backbone-satisfaction gate (COR-007 pattern-extraction): the *same* check runs from both capability-entry paths — `install` (kit-source copy) and `register` (in-repo incubated) — so neither path can activate a capability the current backbone cannot support.
3. **Capability dependencies (COR-030)** — every entry in `requires_capabilities` must be satisfied: the declared dependency is installed *and* its recorded version falls within the declared semver range. Refuse with an actionable hint naming what to install or upgrade first. Never auto-installs.
4. **Naming collision detection** — skills/agents from the new capability must not collide with already-installed names. Interactive resolution available.

### Register pre-flight checks (incubated; COR-031)

`pkit capabilities register` shares the install pre-flights that still apply (backbone-satisfaction, capability-dependencies, collision detection against *other* installed content) and skips "exists in kit source" (the in-repo tree *is* the source). It adds one check the install path doesn't need:

- **Self-consistency validation (COR-031 D1)** — the adopter hand-authored this capability; nothing upstream validated it. Before activation, its own `package.yaml` (parseable capability manifest, valid version, valid `requires_backbone` / dependency ranges), required layout (`README.md`), and own schema pairs (validated by the same validator `pkit schemas validate` runs) are checked against the working tree, which is its spec. Refuse with the structural problems listed. This is *self-validation*, not source-reconciliation — origin suppresses the latter (below), never the former.

### Uninstall: origin-aware removal (COR-031 D4)

`pkit capabilities uninstall` first runs two refusal checks (both defeatable by `--force`):

1. **Declared dependents (COR-030)** — if any installed capability lists this one in its `requires_capabilities`, refuse and name the dependents. The operator must uninstall or upgrade the dependents first.
2. **Textual references** — if any adopter-authored file cites the capability (citation token or path reference), refuse and list the references.

Once those pass, **what gets deleted depends on origin** — origin-blind deletion would destroy adopter-authored work, the exact hazard COR-031 exists to prevent:

- **`kit-shipped`** — the subtree is a disposable copy of kit source. Uninstall deletes the subtree, removes the registry entry, and re-runs deploy (deploy's stale-removal pass then drops the harness symlinks, since the source is gone). Unchanged from before.
- **`incubated-in-repo`** — the subtree is the adopter's *only* copy of authored work. Uninstall **unregisters in place**: it removes the registry entry and drops the capability's deployed harness skills/agents, but **leaves the authored subtree on disk** (the CLI reports "unregistered in place; your authored files are kept at `<path>`"). Because the adapter deploy primitives key stale-removal on whether the *source file* still exists — and here it does — the lifecycle drops those harness entries explicitly rather than relying on a deploy re-run. Deleting an incubated capability's files is a separate explicit opt-in: `--purge` (which confirms first, honouring the pause-before-destructive-ops discipline; `--yes` skips the prompt for non-interactive use). The default never deletes incubated files.

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

1. **Resolve compatibility.** Read each installed component's `requires_backbone` against the target backbone version. Refuse to upgrade backbone past a component's range, unless the component is also being upgraded to a version compatible with the new backbone. Surface conflicts so the adopter can address them (upgrade specific components, pin backbone, or remove an incompatible component). Also checks **capability dependencies (COR-030)**: for each installed capability, verifies that its `requires_capabilities` entries are satisfied using *installed* versions of both sides (backbone upgrade does not change capability versions). Refuses with an actionable hint if any dependency is absent or out of range.
2. **Pull new propagated content.** Run sync (per COR-001) for the backbone. Component-side propagated content updates as part of each component's upgrade.
3. **Run backbone migrations** in order: manifest-schema → structural → resource-scoped, across minor-version boundaries from current to target.
4. **For each component being upgraded**, run its migrations in version order with the same scope ordering within each `<major>.<minor>.0/` directory.
5. **Reconcile derivable state.** Each component's setup primitive re-applies the kit-side spec at its current version + adopter's config (idempotent — labels, files, symlinks, merged settings).
6. **Update recorded versions.** Backbone version in the backbone manifest; component versions in their respective manifests.

Idempotent: running upgrade on a current adopter is a no-op.

### Per-component upgrade

Upgrading just one component (e.g., the project-management capability) skips backbone-side steps as long as the component's new version remains within `requires_backbone` of the current backbone. The same compatibility check from step 1 gates entry. Steps 4 (component migrations), 5 (component-scoped reconciliation), and 6 (component manifest version bump) run; step 2 pulls only the component's source.

#### Upgrading an incubated capability (COR-031 D1/D4)

`pkit capabilities upgrade <name>` is **origin-aware**. For an `incubated-in-repo` capability there is no kit source to resolve against — the working tree *is* the source — so the command **must not** route through the kit-source resolution path. Doing so would mislabel the capability "no longer ships from source" and steer the adopter toward the destructive uninstall. Instead, "upgrade" for an incubated capability **re-applies deploy from the in-repo tree** (mirroring the sync skip-branch below): any newly-authored skills/agents re-materialise in the harness, and source-reconciliation stays suppressed. If the in-repo subtree has gone missing, the command reports that plainly — never as a kit-source orphan, and never suggesting uninstall. A `kit-shipped` capability's upgrade path is unchanged (resolve from kit source, refresh, run migrations).

For capabilities, a **direction-split dependency check (COR-030)** runs before collision detection:

- *Upgrading a dependent* — the new source version's `requires_capabilities` is checked against the installed dependency versions. If a dependency is absent or out of range, the upgrade **refuses with an actionable hint** (the operator controls the dependent version; no deadlock).
- *Upgrading a dependency* — installed capabilities that declare this capability in their `requires_capabilities` are checked against the new version. If the new version falls outside a dependent's declared range, the upgrade **warns loudly and requires `--force` to proceed** — it is not a hard block. A hard block would deadlock (the operator cannot advance the dependency without cascade-upgrading the dependent, which is out of scope per COR-030). Use `--force` as the by-hand analogue of cascade-upgrade, then upgrade the now-desynced dependents to restore consistency.

Both entry points — backbone-wide `pkit upgrade` and single-capability `pkit capabilities upgrade <name>` — share one version-range / installed-state predicate (`capabilities.check_capability_dependencies`). The backbone-wide path does not move capability versions, so only the "dependent against unsatisfied dependency" direction (refuse) applies there; the warn+force direction applies only in the single-capability path.

## Reconciling derivable state

Two commands consume the manifests differently for the same conceptual job — "is reality consistent with the spec at the recorded version?":

- **`validate`** computes the expected state for derivable resources at each recorded version + adopter's config, compares to actual reality, reports drift. Manifest-tracked resources are compared directly: manifest entries vs. backend.
- **`upgrade`** does the same comparison, then *applies* changes to bring reality into line (step 5 of the flow).

Either way, the kit-side spec at the recorded version is the source of truth for what should exist; the manifest tracks only what the spec can't recover (recorded version, opaque IDs).

### The incubated-origin skip-branch (COR-031 D1)

The reconciliation above assumes a kit-side spec to reconcile against — true for a `kit-shipped` capability, false for an `incubated-in-repo` one, whose working tree *is* the spec. So `sync` (and the capability-refresh inside it) **skips source-reconciliation for any capability whose registry `origin` is `incubated-in-repo`**: it does not re-copy from kit source, and it does not emit the "no longer shipped from source" orphan warning that a kit-shipped capability missing from source would trigger. The capability's adopter-owned files are left exactly as authored — the no-shared-files invariant (COR-001) applied to incubated content.

The skip is scoped to *reconciliation against the kit source only*. Everything else is unchanged: deploy primitives still run (the capability's skills/agents re-materialise in the harness), dependency gating still counts the capability as installed, and structural self-consistency validation still applies against the adopter's own tree (which is its spec). Origin governs source-reconciliation, not participation or self-validation.

One boundary case (COR-031): if a same-named capability *now* also ships from kit source — graduation arriving before graduation is specified — `sync` surfaces the collision rather than silently shadowing either tree, so the adopter can decide. The default skip applies only while no kit capability of that name exists.

## Worked example

A full worked example demonstrating the upgrade flow across backbone + components is deferred for a focused rewrite. The prior example was built around the now-retired bundle pattern (per [COR-027](../decisions/core/COR-027-alternative-impls-as-capability-data.md)); rewriting it against the capability + adapter shape is queued.

For concrete examples of the contract this document defines, see:

- The kit's own `.pkit/manifest.yaml` for the backbone-manifest shape with one capability + one adapter entry.
- `.pkit/migrations/backbone/<X.Y.0>/` for backbone migration script structure.
- `.pkit/capabilities/project-management/migrations/0.12.0/` for a capability-tier migration that handles file-rename + adopter-state cleanup.
- `.pkit/adapters/claude-code/migrations/` for adapter-tier migration patterns.
