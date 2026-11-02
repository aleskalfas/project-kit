---
variant: specialized
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/lifecycle/ownership.py
        - .pkit/lifecycle/templates/README.md
        - src/project_kit/__init__.py
        - src/project_kit/lifecycle_ownership.py
        - src/project_kit/manifest.py
        - src/project_kit/validators.py
        - src/project_kit/sync.py
        - src/project_kit/install.py
        - src/project_kit/upgrade.py
        - src/project_kit/capabilities.py
        - src/project_kit/visibility.py
        - src/project_kit/loaded_rules.py
        - src/project_kit/provisioning.py
        - src/project_kit/scaffolds.py
        - src/project_kit/agents.py
        - src/project_kit/agents_overlay.py
        - src/project_kit/decisions.py
        - src/project_kit/storyboards.py
        - src/project_kit/schemas_authoring.py
        - src/project_kit/process_authoring.py
        - src/project_kit/permissions.py
        - src/project_kit/treecopy.py
        - src/project_kit/friction_discovery.py
        - src/project_kit/package_validate.py
        - hatch_build.py
        - .pkit/migrations/backbone/2.0.0/002-move-answers-to-files.sh
        - .pkit/schemas/backbone/package.schema.json
        - .pkit/schemas/backbone/config.schema.json
        - .pkit/schemas/backbone/filler.schema.json
        - .pkit/schemas/backbone/rule-set.schema.json
      record: [COR-001, COR-004, COR-005, COR-010, COR-017, COR-027, COR-030, COR-031, COR-041, "COR-050#1", "COR-052#5", COR-053, "COR-059#2", "COR-059#3", COR-061, "COR-062#9", "COR-062#11", "ADR-057#2", "COR-052#6", "COR-051#5", COR-019, "COR-059#9", "ADR-065#9", "ADR-065#10", "living-docs:DEC-001", ADR-003, ADR-051, "ADR-055#3", ADR-059, "ADR-065#1"]
      artefact:
        - .pkit/lifecycle/manifest.md
        - .pkit/lifecycle/component-registry.md
        - .pkit/lifecycle/migrations.md
        - .pkit/lifecycle/upgrade-flow.md
        - .pkit/lifecycle/manifest.md#capability-origin-cor-031
        - .pkit/lifecycle/manifest.md#field-layout-and-casing
        - .pkit/lifecycle/manifest.md#how-a-data-point-resolves
        - .pkit/lifecycle/manifest.md#how-a-registered-anchor-kind-is-resolved
        - .pkit/lifecycle/manifest.md#how-a-registered-command-is-run
        - .pkit/lifecycle/manifest.md#strict-on-unknown-keys
        - .pkit/lifecycle/manifest.md#validation-the-package-schema
        - .pkit/lifecycle/manifest.md#where-a-capabilitys-manifest-lives
        - .pkit/lifecycle/manifest.md#where-a-project-filler-file-lives-the-address-to-path-mapping
        - .pkit/lifecycle/migrations.md#naming
        - .pkit/lifecycle/migrations.md#script-contract
        - .pkit/lifecycle/migrations.md#three-scopes-per-tier
        - .pkit/lifecycle/migrations.md#which-version-a-migration-targets
        - .pkit/lifecycle/upgrade-flow.md#mandatory-process-connections-cor-053-point-6
        - .pkit/lifecycle/upgrade-flow.md#per-component-upgrade
        - .pkit/lifecycle/upgrade-flow.md#rolling-back-an-upgrade
        - .pkit/lifecycle/upgrade-flow.md#syncs-guard-no-path-down-and-no-migration-passed-over
        - .pkit/lifecycle/upgrade-flow.md#the-dependency-gates
        - .pkit/lifecycle/upgrade-flow.md#the-replay-a-missing-completion
        - .pkit/lifecycle/upgrade-flow.md#the-steps-of-a-transition
        - .pkit/lifecycle/upgrade-flow.md#upgrading-an-incubated-capability-cor-031-d1d4
        - .pkit/lifecycle/upgrade-flow.md#the-capabilities-rules-index
        - .pkit/lifecycle/upgrade-flow.md#what-a-step-newly-binds
        - .pkit/lifecycle/manifest.md#the-methodologys-literals
        - .pkit/lifecycle/manifest.md#package-metadata-packageyaml
        - .pkit/lifecycle/migrations.md#directory-layout
---

# Lifecycle

How project-kit installs, upgrades and removes the backbone and its components, and how their versions move ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)). This page holds the layout, the two tiers and how derivable state is reconciled. Four pages beside it hold the rest of the contract ("The pages beside this one" below).

## Contents

<!-- pkit:contents -->
- [Layout](#layout)
- [The two tiers](#the-two-tiers)
- [Manifest schema](#manifest-schema)
- [The component registry](#the-component-registry)
- [Migration framework](#migration-framework)
- [The upgrade flow](#the-upgrade-flow)
- [Reconciling derivable state](#reconciling-derivable-state)
- [Worked example](#worked-example)
- [The pages beside this one](#the-pages-beside-this-one)
- [Why, and what an adopter does](#why-and-what-an-adopter-does)
<!-- /pkit:contents -->

## Layout

The lifecycle keeps a project's state in these places under `.pkit/`:

```
.pkit/
├── manifest.yaml                                    ← backbone manifest (recorded version + component registry)
├── lifecycle/
│   └── ownership.py                                 ← the ownership predicates (see "Reconciling derivable state")
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
    ├── migrations/<major>.<minor>.0/...             ← in the source only: a transition reads them from the bundle
    └── project/
        └── manifest.yaml                            ← per-component manifest
```

Where a tier's migrations lie, and how each script is named, is [`migrations.md`, "Directory layout"](migrations.md#directory-layout).

**Authoring.** Nobody stamps these layouts by hand. `pkit new adapter <name>`, `pkit new capability <name>` and `pkit new migration` stamp the contract these pages define, and the CLI reference specifies them. The stamps are the CLI's own code, which ships with it. So an upgrade that changes a contract also changes what they stamp.

## The two tiers

The backbone and its components each carry a version of their own, in semantic versioning, `major.minor.patch` (COR-010).

- **Backbone:** the core that ships together, as one release with one version number. It holds the core decisions and the specification, the rules, and the CLI with its runtime.
- **Components:** installable pieces, each versioned on its own, that depend on a range of backbone versions. Capabilities (COR-017) and adapters are components.
  - **No bundles:** alternative implementations within a capability live as the capability's own data, not as bundles in the file system (COR-027).
- **A component's range:** each component declares the backbone versions it works with in its `package.yaml`, as `requires_backbone: ">=X.Y.Z, <W.0.0"` ([`manifest.md`, "Package metadata"](manifest.md#package-metadata-packageyaml)).
- **Patch releases:** a patch release is a backward-compatible fix, and carries no migration. A migration folder is named for its full target version, with the patch always `0`, such as `2.1.0/`. It covers every patch of that minor line.

## Manifest schema

The manifests and the package metadata are on [`manifest.md`](manifest.md). Each heading below leads to its section there.

### Backbone manifest (`<project>/.pkit/manifest.yaml`)

See [`manifest.md`, "Backbone manifest (`<project>/.pkit/manifest.yaml`)"](manifest.md#backbone-manifest-projectpkitmanifestyaml).

#### Capability origin (COR-031)

See [`manifest.md`, "Capability origin (COR-031)"](manifest.md#capability-origin-cor-031).

### Per-component manifest (one per installed component)

See [`manifest.md`, "Per-component manifest (one per installed component)"](manifest.md#per-component-manifest-one-per-installed-component).

#### An adapter's manifest

See [`manifest.md`, "An adapter's manifest"](manifest.md#an-adapters-manifest).

#### Where a capability's manifest lives

See [`manifest.md`, "Where a capability's manifest lives"](manifest.md#where-a-capabilitys-manifest-lives).

### Package metadata (`package.yaml`)

See [`manifest.md`, "Package metadata (`package.yaml`)"](manifest.md#package-metadata-packageyaml).

#### Field layout and casing

See [`manifest.md`, "Field layout and casing"](manifest.md#field-layout-and-casing).

#### Validation: the package schema

See [`manifest.md`, "Validation: the package schema"](manifest.md#validation-the-package-schema).

#### Strict on unknown keys

See [`manifest.md`, "Strict on unknown keys"](manifest.md#strict-on-unknown-keys).

#### The connection, documentation and friction blocks

See [`manifest.md`, "The connection, documentation and friction blocks"](manifest.md#the-connection-documentation-and-friction-blocks).

#### The methodology's literals

See [`manifest.md`, "The methodology's literals"](manifest.md#the-methodologys-literals), with its part "How dependencies are provisioned before an offline run".

#### How a registered command is run

See [`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run), with its parts "A run inside a run" and "The seams back".

#### How a registered anchor kind is resolved

See [`manifest.md`, "How a registered anchor kind is resolved"](manifest.md#how-a-registered-anchor-kind-is-resolved).

#### Where a project filler file lives: the address-to-path mapping

See [`manifest.md`, "Where a project filler file lives: the address-to-path mapping"](manifest.md#where-a-project-filler-file-lives-the-address-to-path-mapping).

#### How the wiring is resolved

See [`manifest.md`, "How the wiring is resolved"](manifest.md#how-the-wiring-is-resolved), with its part "Version relations".

#### How a data point resolves

See [`manifest.md`, "How a data point resolves"](manifest.md#how-a-data-point-resolves), with its part "Reading one point from a script".

#### A data point's question

See [`manifest.md`, "A data point's question"](manifest.md#a-data-points-question).

#### Discovery: what a capability would connect to

See [`manifest.md`, "Discovery: what a capability would connect to"](manifest.md#discovery-what-a-capability-would-connect-to).

## The component registry

The registry, and the checks before an install, a register and an uninstall, are on [`component-registry.md`](component-registry.md). Each heading below leads to its section there.

### Install pre-flight checks

See [`component-registry.md`, "Install pre-flight checks"](component-registry.md#install-pre-flight-checks), with its part "The declared project rule set".

### Register pre-flight checks (incubated; COR-031)

See [`component-registry.md`, "Register pre-flight checks (incubated; COR-031)"](component-registry.md#register-pre-flight-checks-incubated-cor-031).

### Uninstall: origin-aware removal (COR-031 D4)

See [`component-registry.md`, "Uninstall: origin-aware removal (COR-031 D4)"](component-registry.md#uninstall-origin-aware-removal-cor-031-d4).

## Migration framework

The migration framework is on [`migrations.md`](migrations.md). Each heading below leads to its section there.

### What ships a migration

See [`migrations.md`, "What ships a migration"](migrations.md#what-ships-a-migration).

### Directory layout

See [`migrations.md`, "Directory layout"](migrations.md#directory-layout).

### Naming

See [`migrations.md`, "Naming"](migrations.md#naming).

### Which version a migration targets

See [`migrations.md`, "Which version a migration targets"](migrations.md#which-version-a-migration-targets).

### Three scopes (per tier)

See [`migrations.md`, "Three scopes (per tier)"](migrations.md#three-scopes-per-tier).

### Script contract

See [`migrations.md`, "Script contract"](migrations.md#script-contract).

### Tier independence

See [`migrations.md`, "Tier independence"](migrations.md#tier-independence).

## The upgrade flow

The upgrade flow is on [`upgrade-flow.md`](upgrade-flow.md). Each heading below leads to its section there.

### The steps of a transition

See [`upgrade-flow.md`, "The steps of a transition"](upgrade-flow.md#the-steps-of-a-transition).

### Seed paths

See [`upgrade-flow.md`, "Seed paths"](upgrade-flow.md#seed-paths).

### A new collision

See [`upgrade-flow.md`, "A new collision"](upgrade-flow.md#a-new-collision).

### The capabilities' rules index

See [`upgrade-flow.md`, "The capabilities' rules index"](upgrade-flow.md#the-capabilities-rules-index).

### What a step newly binds

See [`upgrade-flow.md`, "What a step newly binds"](upgrade-flow.md#what-a-step-newly-binds).

### A clash of area names

See [`upgrade-flow.md`, "A clash of area names"](upgrade-flow.md#a-clash-of-area-names).

### The dependency gates

See [`upgrade-flow.md`, "The dependency gates"](upgrade-flow.md#the-dependency-gates).

### What the settings merge widens

See [`upgrade-flow.md`, "What the settings merge widens"](upgrade-flow.md#what-the-settings-merge-widens).

### Two recorded states, and an interrupted upgrade

See [`upgrade-flow.md`, "Two recorded states, and an interrupted upgrade"](upgrade-flow.md#two-recorded-states-and-an-interrupted-upgrade).

### Rolling back an upgrade

See [`upgrade-flow.md`, "Rolling back an upgrade"](upgrade-flow.md#rolling-back-an-upgrade).

### The replay: a missing completion

See [`upgrade-flow.md`, "The replay: a missing completion"](upgrade-flow.md#the-replay-a-missing-completion).

### Sync's guard: no path down, and no migration passed over

See [`upgrade-flow.md`, "Sync's guard: no path down, and no migration passed over"](upgrade-flow.md#syncs-guard-no-path-down-and-no-migration-passed-over).

### Per-component upgrade

See [`upgrade-flow.md`, "Per-component upgrade"](upgrade-flow.md#per-component-upgrade).

#### Upgrading an incubated capability (COR-031 D1/D4)

See [`upgrade-flow.md`, "Upgrading an incubated capability (COR-031 D1/D4)"](upgrade-flow.md#upgrading-an-incubated-capability-cor-031-d1d4).

#### Mandatory process connections (COR-053 point 6)

See [`upgrade-flow.md`, "Mandatory process connections (COR-053 point 6)"](upgrade-flow.md#mandatory-process-connections-cor-053-point-6).

## Reconciling derivable state

Two commands consume the manifests differently for the same conceptual job — "is reality consistent with the spec at the recorded version?":

- **`validate`** computes the expected state for derivable resources at each recorded version + adopter's config, compares to actual reality, reports drift. Manifest-tracked resources are compared directly: manifest entries vs. backend.
- **`upgrade`** does the same comparison, then *applies* changes to bring reality into line (step 8 of the flow).

Either way, the kit-side spec at the recorded version is the source of truth for what should exist; the manifest tracks only what the spec can't recover (recorded version, opaque IDs).

### What sync writes

`pkit sync` reconciles a project at the release it records, and moves no version (COR-059 point 2). Among the project's files it writes three kinds of thing, and no other:

- **The methodology's content** at the recorded release: its trees, adapters included, and each installed capability the running pkit ships at the version the project records ("The downgrade guard on capability refresh", below). A project-owned path is never overwritten.
- **Derivable state:** the capabilities' rules index, the deployed skills and agents, `.pkit/.gitignore`, pkit's region of the clone's local exclude file where the project is private, the agent workspace and its line in that file, and the query commands' environments.
- **The project's own paths, through merge delivery only,** in its tier that asks nothing. For Claude Code it merges `.claude/settings.json` and `CLAUDE.md`, adding the methodology's entries and never removing one the project wrote. A tier that asks never runs in sync. Merge delivery may create its own target file where it is missing, such as `CLAUDE.md`, as merge, not as seeding.

It writes no recorded version, no manifest and no seed path, runs no migration, and asks no question a data point declares ([COR-061](../decisions/core/COR-061-point-questions.md) point 4). Before it writes, it stops on a file at the index's path that is not the index ("The capabilities' rules index", above), and after its copy it says what the copy newly binds of each loaded set ("What a step newly binds", above).

### The incubated-origin skip-branch (COR-031 D1)

The reconciliation above assumes a kit-side spec to reconcile against — true for a `kit-shipped` capability, false for an `incubated-in-repo` one, whose working tree *is* the spec. So `sync`, and the propagation step a transition runs, **skip source-reconciliation for any capability whose registry `origin` is `incubated-in-repo`**: it does not re-copy from kit source, and it does not emit the "no longer shipped from source" orphan warning that a kit-shipped capability missing from source would trigger. The capability's adopter-owned files are left exactly as authored — the no-shared-files invariant (COR-001) applied to incubated content.

The skip is scoped to *reconciliation against the kit source only*. Everything else is unchanged: deploy primitives still run (the capability's skills/agents re-materialise in the harness), dependency gating still counts the capability as installed, and structural self-consistency validation still applies against the adopter's own tree (which is its spec). Origin governs source-reconciliation, not participation or self-validation.

One boundary case (COR-031): if a same-named capability *now* also ships from kit source — graduation arriving before graduation is specified — `sync` surfaces the collision rather than silently shadowing either tree, so the adopter can decide. The default skip applies only while no kit capability of that name exists.

<a id="the-downgrade-guard-on-capability-refresh-issue-524"></a>
### The downgrade guard on capability refresh

A `kit-shipped` capability's copy replaces its subtree wholesale. On its own that is direction-blind: a source *older* than the installed version would overwrite newer committed state with stale content — the exact data loss reported where a mis-pinned source refreshed an installed capability back several minor versions. So before it copies a `kit-shipped` capability, `sync` compares the **source** version with the **installed version of record** (the per-component `manifest.yaml`, falling back to the installed `package.yaml` — what the copy would actually overwrite), and copies it only where the two are equal

- **source version < installed version (a downgrade):** skip the capability, print a `skipped` line naming both versions, and leave the installed tree untouched. Nothing overrides it: a recorded version never moves down. `sync --force`, which once overrode it, is accepted for one release, ignored, and reported on stderr. A later release removes the flag. Under `--dry-run` the skip is reported as the run would report it.
- **source version > installed version:** skip it too, reported `pending`: moving a capability is `pkit upgrade`'s, with its migrations.
- **equal:** copy it, with no migration and no stamp.

A version that cannot be read on the installed side skips the capability, so none of its migrations runs anywhere. One the bundle's package does not name skips it as well. The incubated skip-branch above is unchanged (no kit source to compare against), and so is the "no longer ships from source" orphan case. `pkit upgrade`, the transition of the backbone, refuses a capability its bundle ships older, in its step 1, before it writes anything ("The upgrade flow", above). So does `pkit capabilities upgrade`, the transition of one capability ("Per-component upgrade", above). Before any capability is reached, sync's guard has already stopped a running pkit at another version than the project's, in `sync` and in both capability commands ("Sync's guard" above).

### The ownership predicates (`ownership.py`)

The tier map above — which trees the kit owns, which are the project's, and how a capability's `origin` changes the answer — is also a question *other* layers need to ask. `.pkit/lifecycle/ownership.py` answers it as `is_sync_managed(target_root, path)`, and every consumer imports that one definition.

It answers a **second, narrower** question beside it: `is_adopter_owned_by_tier(rel_posix)` — *does this `.pkit/`-relative path sit on the project side of the no-shared-files split, by tier alone?* The two are not interchangeable, and picking the wrong one is a real error. `is_sync_managed` additionally consults a capability's **registration** (an unregistered or `incubated-in-repo` capability is not sync-managed whatever its tier) and reads everything *outside* `.pkit/` as unmanaged — so `src/`, which legitimately ships, answers False. A caller asking "may this be distributed?" needs the tier predicate; a caller asking "is this the kit's to manage, so an agent may not claim write authority over it?" needs `is_sync_managed`. Note what that second question is **not**: `pkit sync` does not call it. Sync decides what it writes through the copy path's own ownership handling, so a wrong answer here cannot overwrite an adopter's file — it can only misplace write authority. The name invites the other misreading. Pass **`is_adopter_owned_by_tier`** a file path: its depth-free `project/` case reads every part except the last, so a directory path naming the tier itself (`agents/project`) answers False — though its other cases do match on a final component, so this is a rule about that case rather than about the whole predicate. `is_sync_managed` is deliberately the other way: it matches the declared tier positions by *prefix*, so the tier directory itself answers "the adopter's" — its consumer passes overlay entries, which are usually directories. "Is this *directory* the adopter's tier?" is a different question, and the packaging hook declares its own answer rather than asking this predicate.

It lives here rather than in the CLI package for the reason for the permission decision core: an adapter's deploy primitive runs **in the adopter's tree**, where the globally-installed `pkit` runtime is not importable. Propagated in-tree code is the only home both the CLI and a propagated adapter script can reach, so the area is propagated and the module ships with it. Dependency direction is inward — the CLI imports it, each adapter imports it, and it imports neither.

`is_sync_managed`'s first consumer is the agent-overlay write-authority check. A *write-carrying* overlay category may not name sync-managed content, which is the no-shared-files invariant applied at the agent surface. The module also declares that category set (`WRITE_CARRYING_CATEGORIES`), beside the predicate that guards it. Re-deriving either per adapter would fork the ownership rule and silently skip the check on the next harness, so a test fails any adapter script that carries a copy.

`is_adopter_owned_by_tier`'s consumers are the packaging build hook (`hatch_build.py`) and the test that holds it honest — plus one expression of the rule that deliberately does not call it: the sdist's `withhold` globs, a build-hook option in `pyproject.toml` that mirrors the same cases by hand. The hook could apply the predicate to the sdist as well; it does not, so that the sdist's filter stays independent of the wheel's and the test comparing the two artifacts can catch a hole in the predicate. That copy is the one to check first when the two distributions disagree. The wheel bundles the methodology tree by force-include, and hatchling's `exclude` cannot filter force-included paths — so the manifest carried its own idea of which paths were adopter-owned, **disagreed with this module, and nothing could notice**: 51 adopter-owned files shipped, including git-ignored runtime state that made the artifact depend on the build machine. Deriving the boundary from this predicate is what closes that, and it is the same lesson one altitude down — a second copy of an ownership rule forks silently.

`is_sync_managed` is deliberately **conservative under `.pkit/`**: anything the map does not recognise as project-owned reads as sync-managed. A false "not managed" would hand out write authority over kit content, which is the costlier direction and why the bias points this way. But the cost of a false "managed" was understated here as "a rejected overlay entry the adopter re-points": when the misjudged path is the adopter's *own* file, there is nowhere else to point, and they are simply locked out of it. The bias stays; the map has to be right about the adopter's tier at every depth for the bias to be safe.

A **third** question builds on the first: `is_synced_copy(target_root, path)` — *does this path arrive here as a copy, written by a sync from the methodology's source or pulled whole from the external source a capability is pinned to (COR-041)?* Documentation places ask it: a synced copy is never a place, so that a sync never shows up as friction in the project's own history ([living-docs:DEC-001-living-docs-discipline] point 1). Its consumers are the friction pass, which loads this module from the tree and tests every match of every declared place with it (`synced-place`, the schemas README, "The friction block"), artefact discovery, which asks it of each rule-set file it walks, since a rule a synced copy holds owes the project no answer ([COR-062](../decisions/core/COR-062-answers-in-own-files.md) point 9), the packages pass of `pkit validate`, which asks it of a package file to name the fix that lasts (the journal warning in "Validation: the package schema"), and the `pkit new`, `pkit process new`, `pkit process couple`, `pkit process hand-off` and `pkit permissions scaffold` stamps, through `synced_copy_refusal` of `src/project_kit/lifecycle_ownership.py` (see [the CLI reference, "Folders a sync writes"](../cli/README.md#folders-a-sync-writes)). It answers true for a file of a registered `externally-sourced` capability outside its `project/` tier, in every repository. Otherwise it is `is_sync_managed` **and** the repository not being the methodology's own source (`is_methodology_source`). The source repository is the one whose `.pkit/` is the methodology's own tree. The tool recognises it by sync's self-host test, which the ownership module cannot import, so the predicate recognises it by the marker in "The methodology's literals" above — the package source beside the `.pkit/` tree, the same test the entry-point router runs (the dispatcher is not a marker).

The router's first route is what keeps the predicate's answer equal to sync's. And tests hold the predicate both to the router's markers and to sync's own decision. The difference from `is_sync_managed` is deliberate. In the source repository the kit's trees stay the kit's to manage — write authority does not move.

Yet none of them is a copy, because the tree is what a sync would copy from. Its self-host sync re-runs the deploy primitives and propagates nothing. In an adopter, the backbone's trees and a `kit-shipped` capability's are copies. An `externally-sourced` capability's are copies in the source too, since it is authored in another repository.

An `incubated-in-repo` capability, an unregistered one and every `project/` tier are not. The verdict keys on origin and on the repository, never on the path, so the same `.pkit/` README is a place in the source and refused in an adopter.

## Worked example

See [`manifest.md`, "Worked example"](manifest.md#worked-example).

## The pages beside this one

Each part of the lifecycle that this page does not hold has a page of its own:

- [`manifest.md`](manifest.md): the backbone manifest, each component's manifest, and package metadata. That includes the methodology's literals, how commands and anchor kinds run, filler files, the wiring, data points and discovery.
- [`component-registry.md`](component-registry.md): the registry, the checks before an install and a register, and uninstall.
- [`migrations.md`](migrations.md): what ships a migration, its folder, name and target version, its scope, and the script contract.
- [`upgrade-flow.md`](upgrade-flow.md): the steps of a version transition, its guards, rolling back, and the upgrade of one capability.

Each heading that left this page keeps its address here, as a heading that leads to its new home.

## Why, and what an adopter does

This section keeps the reasons behind the contract on the pages beside this one, and the tasks an adopter carries out by hand. Each item links the section it explains.

### Behind the manifests and package metadata

- **Capability origin (COR-031)** ([`manifest.md`](manifest.md#capability-origin-cor-031)): why origin lives in lifecycle-owned install-state, never inside the capability's own subtree. An incubated capability's subtree is adopter-owned. Writing lifecycle state into it would re-create the ownership blur the origin distinction exists to prevent (COR-031 D2).
- **Where a capability's manifest lives** ([`manifest.md`](manifest.md#where-a-capabilitys-manifest-lives)): why there, under the capability's `project/`. Every ownership predicate treats a capability's `project/` as the project's (["The ownership predicates"](#the-ownership-predicates-ownershippy)). So no copy of the capability's tree deletes or overwrites the manifest, and the bundle ships none.
- **Field layout and casing** ([`manifest.md`](manifest.md#field-layout-and-casing)): why role names and addresses are words. The schema first shipped a looser pattern, in which each part was any run of characters but whitespace and `:`. That pattern admitted roles no selection key could name and no filler path could hold. The schema refuses them now.
- **Field layout and casing** ([`manifest.md`](manifest.md#field-layout-and-casing)): why both spellings stay.
  - **The kebab-case keys:** a record that names the keys people write decides their spelling (COR-053 point 3 and its Rationale). COR-050 point 1 says the same of the friction block.
  - **`schema_version` inside the blocks (COR-052 point 5, COR-053 point 10):** it keeps its snake_case there because it is the field that carries a point's version. It carries it everywhere that version is written: a filler envelope, a role block's point block.
  - **No rename:** no record decides a casing rule for the whole file. Renaming either family would be a surface change owing a migration (COR-010) for no reader's benefit.
- **Validation: the package schema** ([`manifest.md`](manifest.md#validation-the-package-schema)): why `pkit new capability` refuses a name a backbone command holds, and `capabilities install` and `register` do not. Refusing at install would make an upgrade break the installation of something that worked. The check across packages names the problem instead.
- **Validation: the package schema** ([`manifest.md`](manifest.md#validation-the-package-schema)): why none of the three type checks fails. The project cannot mend a component's package metadata.
- **Strict on unknown keys** ([`manifest.md`](manifest.md#strict-on-unknown-keys)): why the schema turned strict now, and not from the start.
  - **Why now, and not from the start.** The schema shipped permissive: an unknown key only warned. The blocks the newer records ask for were still being added then, one change at a time. A strict schema would have refused a package ahead of the schema knowing its block.
  - **The blocks.** Every block those records name is now declared: `commands` with the query-contract declaration, `validators`, `connections`, `docs.locations`, and `friction` places and surface. `connections` covers roles, extension points, and extensions with the generated `depends-on` and the mandatory mark.
  - **A misspelling passes silently.** From here an unknown key is a misspelling or a key nothing reads. Every reader of the file passes over a key it does not look for, silently, and a warning beside passing checks does not prevent that. `mandatroy:` on a contribution leaves the connection optional, and `foootprint:` keeps its paths out of `.git/info/exclude`.
  - **Failing stops it.** Failing makes the mistake stop where it is written. It also puts the package file with the rest of the backbone's file schemas, which refuse unknown keys. Those cover the configuration file, rule sets and the filler envelope.
- **Strict on unknown keys** ([`manifest.md`](manifest.md#strict-on-unknown-keys)), what an adopter sees, and does: a note for people belongs in a YAML comment. A new key arrives through the record that decides it and a schema release, never by writing it first.
- **Strict on unknown keys** ([`manifest.md`](manifest.md#strict-on-unknown-keys)), no version bump and no migration: why.
  - Bumping the package file's `schema_version` would make every package file change for no reader's benefit.
  - No script can correct the adopter-owned files that can now fail. None can know what a misspelt key meant, or write a capability's description.
- **The run** ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run)): why a report of a run shows only a trimmed tail of standard error. Only the last lines and bytes are shown, with every terminal escape sequence and control character removed. So a command's words can neither flood nor rewrite the operator's terminal.
- **A run inside a run** ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run)): why the deadline is written on the wall clock. A monotonic clock gives two processes no reference point they can share portably.
- **A tool the backbone runs itself** ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run)): why `gh` runs in the caller's process group. project-management runs `pkit pull-request` in a session of its own, and ends that group at its bound. A `gh` request that went on after project-management had read the pull request to decide could act on it unseen.
- **The policies** ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run)): why the report builder is bounded like every other run. The workstream only enriches a report. So waiting on it past the bound would let a hung tracker call hold the whole report back.
- **The seams back** ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run)): why a script never computes again what the backbone computes. Computing it again would be a second home for one computation.
- **How a registered anchor kind is resolved** ([`manifest.md`](manifest.md#how-a-registered-anchor-kind-is-resolved)):
  - **Why this shape.** The engine must tell whether what an anchor denotes changed between two points: the revalidation point and now, or the change check's base and head.
  - A resolver reads the files on disk alone: it takes one subject and cannot read the project at an older commit. So it answers where the anchored thing lives.
  - The engine does what it does for a path anchor: it reads those files' history from git.
  - Nothing is stored: the friction block keeps no fingerprint and gains no field. The resolver needs no history, no points and no knowledge of the engine.
- **Rule-set sources** ([`manifest.md`, "How a registered anchor kind is resolved"](manifest.md#how-a-registered-anchor-kind-is-resolved)): why a source whose resolver gives no answer fails rule-set validation. A pass nobody earned costs more than the second run a failure costs.
- **Where a project filler file lives: the address-to-path mapping** ([`manifest.md`](manifest.md#where-a-project-filler-file-lives-the-address-to-path-mapping)): why the mapping is path-safe and injective, and why it uses directories.
  - **Path-safe and injective.** The mapping must be path-safe because an address contains `::` and `:` (COR-053 Implications). It must be injective on valid addresses, so that no two points share a file and no path binds the wrong schema.
  - **Why it is injective.** Let two valid addresses map to the same path. Both paths carry the same prefix and the suffix `.yaml`, and removing them leaves equal strings, `p/r/q` and `p'/r'/q'`. No word contains `/`, so each string has exactly two slashes. Splitting at them gives `p = p'`, `r = r'` and `q = q'`: the same address.
    - The argument uses a single fact, **`/` is not a word character**. As strings, then, the mapping stays injective under any word grammar that keeps `/` out. A word containing `/` could not name a directory anyway. On disk it needs one more fact, the lower case below.
  - **Why it is path-safe.** Each address part becomes exactly one path segment, and the word alphabet keeps every segment ordinary:
    - no `:` reaches the path: the address's separators become `/`
    - no `.`, so no segment is `.` or `..`, and the suffix's is the only dot
    - a letter first, so no segment is empty or starts with `-`
    - no upper case, so a case-insensitive filesystem cannot fold two distinct paths into one. The mapping stays injective on disk, not only as strings.
    - no whitespace, quote or glob character, so a path needs no quoting in a shell or a glob
  - **Why directories rather than one file name.** Folding the address into a single name needs a separator no word contains. `<publisher>__<role>__<point>.yaml` works today, since `_` is not a word character. But its correctness then rests on a character the grammar merely happens to exclude. A grammar that later admitted `_` would break the inverse without a trace.
    - Folding on `-`, as `<publisher>--<role>-<point>.yaml`, is not injective at all, because `-` is a word character: `a--b-c-d` is both `a::b:c-d` and `a::b-c:d`.
    - The directory form rests on the one separator no path segment can contain. It lists fillers by publisher and by role in any file browser, and inverts by splitting, not parsing.
- **How a data point resolves** ([`manifest.md`](manifest.md#how-a-data-point-resolves)): what a command filler never reads, and who chooses a point's inert policy.
  - **What a command filler reads.** A filler never reads a base named for one run, because such a base belongs to a comparison. A value that followed it would be answered per run, a parameter by another route. Nor does a filler compare the branch at hand with settled state. That comparison answers about a change: a process point's question or the consumer's work.
  - **Which policy a point declares.** The point's definer chooses the inert policy, because the backbone cannot tell how a value is read.

### Behind the migration framework

- **Naming** ([`migrations.md`](migrations.md#naming)): why each number is used once in a folder. Two scripts of one number would run in the order their slugs give, which nobody chose.
- **Which version a migration targets** ([`migrations.md`](migrations.md#which-version-a-migration-targets)): why the stamp and the check read as they do.
  - **The stamp:** it joins no folder further ahead, since a change may target a later release on purpose.
  - **The check:** it reads the base's tip, not the branch point, since a release that lands after the branch was cut releases the folder too.
- **Three scopes (per tier)** ([`migrations.md`](migrations.md#three-scopes-per-tier)): why manifest-schema migrations run first in any upgrade flow that touches them. The runtime needs to read the manifest correctly before tracking subsequent migrations.
- **Script contract, "What it never runs"** ([`migrations.md`](migrations.md#script-contract)): why a migration script runs none of those commands. COR-004 makes a transition one operation, with propagation, migrations, seeding and merge as its parts. Such a command would repeat a part, or add another operation, inside the transition (COR-059 point 3).

### Behind the upgrade flow

- **The steps of a transition** ([`upgrade-flow.md`](upgrade-flow.md#the-steps-of-a-transition)): why step 1 refuses a component its bundle ships older. Copying it would move its recorded version down, under migrations that run forward only.
- **The dependency gates** ([`upgrade-flow.md`](upgrade-flow.md#the-dependency-gates)): why no flag overrides a moving capability's refusal. The project controls that dependency.
- **Rolling back an upgrade** ([`upgrade-flow.md`](upgrade-flow.md#rolling-back-an-upgrade)): the steps an adopter takes with git.
  - **Undoing an upgrade:** commit the upgrade on its own, and roll it back by reverting that commit, `git revert <commit>`. The revert brings back every file the upgrade's commit changed, inside `.pkit/` and outside. It removes each file the commit added, such as the answer files of the 2.0.0 move in `.pkit/project/friction/answers/`. The manifest, with its two recorded versions, is among them, and so is the pin file where the upgrade wrote it.
  - **An upgrade not yet committed,** such as one a failing migration stopped, is undone over every file `git status` lists, inside `.pkit/` and outside. Restore each file it lists as changed or deleted, with `git restore --staged --worktree <path>`, and delete each new file the upgrade added.
- **The replay: a missing completion** ([`upgrade-flow.md`](upgrade-flow.md#the-replay-a-missing-completion)):
  - **Why it is safe:** every backbone migration acts only on a positive sign that its change is needed. It never deletes by a path's name or position alone ([`migrations.md`, "Script contract"](migrations.md#script-contract)).
- **Sync's guard: no path down, and no migration passed over** ([`upgrade-flow.md`](upgrade-flow.md#syncs-guard-no-path-down-and-no-migration-passed-over)):
  - **Why sync stops in both directions:** a sync at another version would copy another release's content. An older release's content would land over newer content. A newer release's would land without the migrations between the two.
  - **Why `upgrade` checks the older direction only:** upgrade moves the project to the running version, so a newer pkit is what it is for.
  - **Why `upgrade` refuses under the router's fallback:** an installed pkit older than the pin or the content would take the project back. A newer one would move the project and its pin to its own version, not to a release the upgrade resolved.
- **Per-component upgrade** ([`upgrade-flow.md`](upgrade-flow.md#per-component-upgrade)): why its checks refuse a capability bundled older. Copying it would move its recorded version down.
- **Upgrading an incubated capability (COR-031 D1/D4)** ([`upgrade-flow.md`](upgrade-flow.md#upgrading-an-incubated-capability-cor-031-d1d4)):
  - **Why the kit-source path is closed to it:** routing an incubated capability through it would mislabel the capability "no longer ships from source". It would also steer the adopter toward the destructive uninstall.
  - **Why the source repository's upgrade runs no migration:** migrations carry an adopter's copy forward, and there is no copy.
  - **Why upgrading a dependent has no override:** the operator controls the dependent version, so there is no deadlock.
  - **Why upgrading a dependency is no hard block:** a hard block would deadlock. The operator cannot advance the dependency without cascade-upgrading the dependent, which is out of scope per COR-030.
- **Mandatory process connections (COR-053 point 6)** ([`upgrade-flow.md`](upgrade-flow.md#mandatory-process-connections-cor-053-point-6)):
  - **Why the side carrying the mark has no override:** the operator chooses which version of the carrier to install, so nothing deadlocks.
  - **Why the side the mark targets is never a hard block:** a hard block could deadlock.
