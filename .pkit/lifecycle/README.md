---
variant: specialized
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/lifecycle/**
        - src/project_kit/__init__.py
        - src/project_kit/manifest.py
        - src/project_kit/capabilities.py
        - src/project_kit/capability_plans.py
        - src/project_kit/connections.py
        - src/project_kit/data_points.py
        - src/project_kit/run_cache.py
        - src/project_kit/command_runner.py
        - src/project_kit/provisioning.py
        - src/project_kit/package_validate.py
        - src/project_kit/friction_discovery.py
        - src/project_kit/process_dependencies.py
        - src/project_kit/migrations.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
        - src/project_kit/treecopy.py
        - src/project_kit/lifecycle_ownership.py
        - .pkit/schemas/backbone/package.schema.json
        - .pkit/schemas/backbone/filler.schema.json
        - hatch_build.py
      record: [COR-010, COR-017, COR-027, COR-030, COR-031, COR-052, COR-053, ADR-056, ADR-057, ADR-059]
    revalidated:
      at: 2026-10-02T14:53:44Z
      outcome: updated
---

# Lifecycle

How project-kit installs, updates, and removes resources — and how versions evolve across the backbone and its components.

The architecture lives here. The rules and rationale (why two tiers, why per-component manifests, why migrations split by scope and tier) live in `.pkit/decisions/core/COR-010-resource-lifecycle.md`. This document is the spec: manifest schema, upgrade procedure, migration layout, register/unregister mechanics, version-resolution semantics, and worked examples.

Paths and exact YAML shapes are illustrative — the install/sync runtime (per the build roadmap + COR-004) settles them. The shapes here are what every other area of the kit can rely on once the runtime ships.

Developers don't stamp these layouts by hand. The kit ships authoring commands (`pkit new adapter <name>`, `pkit new capability <name>`, `pkit new migration [...]` — specified in `.pkit/cli/README.md` and grounded in COR-005 + COR-017) that scaffold the contract this document defines. The scaffolds are stamped by the CLI's own code, which ships with the binary, so a kit upgrade that changes a contract also updates what gets stamped.

## Layout

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
    ├── migrations/<major>.<minor>.0/...
    └── project/
        └── manifest.yaml                            ← per-component manifest
```

## The two tiers

**Backbone** — the cohesive core that ships together: decisions (CORs and the spec), rules, the CLI / runtime. One coordinated release, one version number.

**Components** — installable, independently-versioned pieces that depend on a backbone version range. Capabilities (`project-management`, `evidence`, `software-engineering`, `demo-recording`, `software-analysis` and `living-docs` today; per COR-017) and adapters (`claude-code` today; future `codex` / `cursor` / etc.) are components. Each component declares a semver range of compatible backbone versions in its `package.yaml`. (Per COR-027, the bundle pattern was retired — alternative implementations within a capability live as capability-internal data, not as filesystem-level bundles.)

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

### Package metadata (`package.yaml`)

Every component — a capability or an adapter — ships a source-side `package.yaml`: the metadata the lifecycle reads at install and upgrade time, the dispatcher reads for commands, and `pkit validate` checks. This section is the **package-metadata reference** the core records leave field layout and casing to (COR-053 point 3). It also records this distribution's literals and where a project's filler files live, which the records leave to the same reference.

```yaml
schema_version: 1                 # 1 or 2 — see "Field layout and casing"
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

# Optional: this component's runtime-local files to git-ignore
# (ADR-009 rule 7). Aggregated into the pkit-owned `.pkit/.gitignore`.
runtime_ignore:
  - .pkit/capabilities/<name>/project/some-runtime.log
```

#### Field layout and casing

The table lists every key `.pkit/schemas/backbone/package.schema.json` knows, with its shape and the record that owns it. **The schema is the authority**: where the table and the schema disagree, the table is the defect. A key the schema does not know is an error, at any level ("Strict on unknown keys", below).

**Required.** The schema requires of every component, capability and adapter alike, the fields COR-017 lists: `schema_version`, `component` with `kind`, `name` and `version` inside it, `description` and `requires_backbone`. Every other top-level key is optional.

| Key | Shape and meaning | Owning record |
|---|---|---|
| `schema_version` | Required: the package file's own version, the integer `1` or `2`, both accepted. See "Validation" below for what each marks. | COR-017; COR-021 (the `2`) |
| `component` | `kind` — `capability` or `adapter`; `name` — a component name (lowercase letters, digits and hyphens, starting with a letter and not ending with a hyphen) equal to the component's directory; `version` — the component's own semver, which gates dependency edges. | COR-010, COR-017 |
| `description` | Required: a non-empty line, the summary `pkit capabilities list` shows, which the dispatcher also uses as the command group's help. | COR-017; COR-021 |
| `requires_backbone` | Required: a version range of compatible backbone versions; must parse. Evaluated at install and upgrade, and checked by `pkit validate` against the installed backbone ("How the wiring is resolved", below). | COR-010, COR-017 |
| `requires_capabilities` | A list of `{name, version}`, both required: a component name and a version range, which must parse. Gated at install, upgrade and uninstall, and checked by `pkit validate` against the installed versions; absence means no dependencies. | COR-030 |
| `commands` | The command tree registered under `pkit <capability>`. A key is a token. A value carrying `script` is a leaf and also needs `help` (one line); `script` is a path relative to the component root and must exist. A leaf may declare `query-contract: true` — the one constant declaration that the command is a query (bounded, deterministic, read-only, needing no network; COR-050 point 2, ADR-057 point 3), required on the command a validator names, on a command filler and on an anchor kind's resolver. A command filler's leaf may also declare `reads`, a non-empty list of distinct values among `history` and `settled`: what it reads beyond the working tree — absent, the working tree only ("How a data point resolves"); `reads` on a leaf without `query-contract: true` is the `packages` member's error. Any other value is a group of further tokens. | COR-021; ADR-057 and ADR-058 (the declaration); COR-052 point 6 (`reads`) |
| `aliases` | A list of unique component names: other namespaces for the same command tree (`pm` for `project-management`). The dispatcher binds them in one precedence walk: a backbone command wins, then a capability's own name, then the first capability in manifest order to declare the alias. An alias that loses reaches nothing, and `pkit validate`'s `packages` member warns at the entry, naming what holds the name — the backbone command, or the capability whose name or earlier alias it is ("Validation: the package schema"). A warning, since the alias is a shorthand: `pkit <capability> …` still reaches the capability. | none — the dispatcher's, beside COR-021 |
| `validators` | A mapping from a validator name (a word) to its entry: `command`, required — a command reference (below) naming a leaf of this component's `commands:` tree, which must exist and declare `query-contract: true`; the leaf's `help` is the validator's — plus optional `order` (an integer; the backbone's members take the orders below 1000, and 1000 is the default). `pkit validate` runs each as a member addressed `<component>:<name>`: the leaf's script from the project root with the one argument `--json`, the offline marker set ("The methodology's literals" below), under the query policy of the one command runner ("How a registered command is run" below) — in its own process group, bounded by the backbone's thirty seconds and killed as a group when it overruns — answering on stdout with one JSON document and nothing else — `{"summary": [...], "findings": [{"severity", "location", "message"}]}`, severity one of `error`, `warning`, `info`, `report`, a finding optionally carrying a `label`; diagnostics go to stderr; only `error` fails. No answer — a leaf without the declaration, an abnormal exit, a timeout, not exactly that document — is an error finding. The living-docs capability registers the first, `living-docs:spaces`. | ADR-058 |
| `provides` | A mapping from hook name to an implementation string. Reserved; no shipped file uses it. | COR-013 |
| `footprint` | A list of unique relative paths or globs: what the component deploys outside `.pkit/`, aggregated across components and routed into `.git/info/exclude` by `pkit visibility private`. | ADR-009 rule 1 |
| `runtime_ignore` | A list of unique relative paths or globs: runtime-local files to git-ignore, aggregated into the pkit-owned `.pkit/.gitignore`. The tier that writes a runtime file declares its pattern, whoever owns the directory it lands in; the backbone, which has no `package.yaml`, declares its own through a core-level seam — the process journals among them, which its engine writes and it ignores unless the project commits them. While they are committed, the render leaves out a component entry declaring them and names it in a comment line, and the entry is warned ("Validation: the package schema"). | ADR-009 rule 7; COR-033 point 7 |
| `connections.roles` | A list of unique qualified role names, `<publisher>::<role>`: the roles this component provides. Every point it defines sits under one of them. | COR-053 points 1 and 3 |
| `connections.extension-points.accepts` | A mapping from point address, `<publisher>::<role>:<point>`, to a data point this component defines: `schema_version`, `schema` (its companion JSON Schema, relative to the component's `schemas/`; must exist) and `description`, all required, plus optional `combination` (`single`, `union` or `additive`; `single` when absent), `default` (`{value, participation}`, both required: the definer's own value, and `always` or `alone` — see "How a data point resolves"), `inert` (`fallback` or `fail`; `fallback` when absent) and `mandatory`. | COR-053 point 2; COR-052 points 1 to 3, 5 and 6 |
| `connections.extension-points.offers` | A mapping from point address to a process or event this component offers: `kind` (`process` or `event`), `schema_version` and `description`, all required. `kind: process` also requires `process`, the offered definition's id; `kind: event` also requires `command` (the emitting command), `schema` (the payload's companion under `schemas/`; must exist) and `subject` (the payload field naming the subject). | COR-053 point 2; COR-036 |
| `connections.extensions.contributes` | A list of contributions to another role's data point: `point` (an address) and `schema_version`, required, plus the data, as `value` (written here) or `command` (a command filler, whose `commands:` leaf must declare `query-contract: true`) — one of the two, not both — and optional `description` and `mandatory`. | COR-053 point 3; COR-052 points 2 and 6 |
| `connections.extensions.subscribes` | A list of subscriptions to another role's event: `point`, `schema_version` and `command` (the subscriber), all required, plus optional `description` and `mandatory`. | COR-053 points 2, 3 and 9 |
| `connections.extensions.depends-on` | **Generated, never hand-written**: `generated: true`, required, and `entries`, a list of `{process}` plus optional `schema_version` and `mandatory`; `process` is in the implementation form `<capability>:<process-id>` or the role form `<publisher>::<role>:<point>`. Written by `pkit capabilities refresh <name>` from the process definitions' `depends_on` — one entry per distinct upstream and targeted interface version, sorted; `schema_version` is the definition entry's `version`, `mandatory` its mark. A copy that differs is a validation error. | COR-053 point 4; COR-038 |
| `mandatory` — on a data point, a contribution, a subscription or a `depends-on` entry | `{reason}`, a non-empty reason required: the mark without one is refused. An offered point takes no mark. | COR-053 point 6 |
| `docs.locations` | A mapping from a location name (`[a-z][a-z0-9-]*`) to `{path}` plus optional `root` (`internal`, the default, or `user`) and `description`; `path` is a sub-path of that documentation root. A location recorded for the name in `.pkit/capabilities/<name>/project/docs-locations.yaml` wins over the declared one; every reader of a capability's locations — the documentation-roots readers and friction discovery — reads them this one way (`project_kit.docs_roots.read_capability_locations`). An entry in another shape places nothing, and a place naming it is a validation finding. | COR-049 points 4 and 5 |
| `friction.places` | A list of `{path}` plus optional `location` (a name declared in `docs.locations`, inside which `path` applies; without one, `path` is repository-relative) and `description`. | COR-050 point 1 |
| `friction.surface` | A list of unique repository-relative paths or globs this component says ought to be described; the part no artefact anchors to is reported as uncovered. | COR-050 point 8 |
| `friction.held` | A list of `{location, path}` plus optional `description`: `path` is a folder — never a glob — inside the declared location `location` names. Its files are the component's held documents, which no place reads as artefacts. | COR-050 point 1 |
| `friction.kinds` | A mapping from an anchor kind (a word, as an anchor block and a rule's cited source write it) to its entry: `command`, required — a command reference naming the leaf of this component's `commands:` tree that resolves an anchor of the kind; the leaf must exist and declare `query-contract: true`. Read for installed capabilities. How the backbone runs the resolver and reads its answer: "How a registered anchor kind is resolved" below. | COR-050 point 2; ADR-057 point 3 |

What holds across the table:

- **Two kinds of `schema_version`.** At the top level it versions the package file. Everywhere else — a data point, an offered point, a contribution, a subscription, a `depends-on` entry — it is the *point's* version, an integer from 1, and two versions are compatible when they are equal (COR-053 point 5).
- **Command references** — `command` on an offered event, a contribution, a subscription, a validator entry or an anchor kind's entry — are a path through the `commands:` tree, tokens separated by single spaces (`create page`), landing on a leaf that exists.
- **Paths** — every `script`, `schema`, `docs.locations` path, `friction` place, held folder and surface entry, `footprint` and `runtime_ignore` entry — are relative, with no `..` segment; the repository check names the offending segment.
- **Role names and addresses are words.** Every part of a qualified role `<publisher>::<role>` and of a point address `<publisher>::<role>:<point>` — in `connections.roles`, the keys of `accepts` and `offers`, a contribution's or subscription's `point`, and a generated `depends-on` entry's `process` — is a word, `[a-z][a-z0-9-]*`: the words the configuration file's selection keys admit and the filler mapping below needs. The word is defined once, as the citation grammar's (`project_kit.refs.ADDRESS_WORD_PATTERN`, COR-019), and a test holds the package and configuration schemas' patterns to it. The schema first shipped a looser pattern — each part any run of characters but whitespace and `:` — which admitted roles no selection key could name and no filler path could hold; it refuses them now.
- **Values are the point's.** A `default.value` or a contribution's `value` is any YAML the point's companion schema admits; the package schema does not type it, and the data point's resolution judges it ("How a data point resolves").

**Casing.** Two spellings meet in this file, and both stay.

- The keys that predate the connection-points record are snake_case — `schema_version`, `requires_backbone`, `requires_capabilities`, `runtime_ignore` — like the backbone's other YAML (the manifests above; the schemas README, "YAML conventions").
- The compound keys COR-053 decides by name are kebab-case — `extension-points`, `depends-on` — written as the record spells them, because a record that names the keys people write decides their spelling (COR-053 point 3 and its Rationale; COR-050 point 1 says the same of the friction block).
- Every other key inside `connections`, `docs` and `friction` is a single word. `schema_version` keeps its snake_case there because it is the field that carries a point's version everywhere that version is written — a filler envelope, a role block's point block (COR-052 point 5, COR-053 point 10).
- One near-collision to mind: the generated `depends-on` here is copied from the process definitions' `depends_on` (COR-038) — one fact in two files, each spelt as its own record spells it.

No record decides a casing rule for the whole file, and renaming either family would be a surface change owing a migration (COR-010) for no reader's benefit. **A new key** is spelt as the record that decides it spells it. Where no record names it, it is a single word if one suffices; a compound is kebab-case inside `connections`, `docs` and `friction`, and snake_case at the top level, like the keys it sits beside.

#### Validation: the package schema

Every `package.yaml` validates against one backbone file schema, `.pkit/schemas/backbone/package.schema.json` (Draft 2020-12; the class is described in the schemas README's "Backbone file schemas" section and placed by ADR-056). It is read from the tree of the project being validated, never from a copy in the binary, so a tree recorded before it landed skips the shape checks and reports so. The validator is `project_kit.package_validate`; two callers run it on the same code: `pkit validate` (the **`packages`** member, over every capability and adapter the backbone manifest registers — ADR-058) and the register pre-flight below (for the one incubated capability about to be activated).

- **Two `schema_version` values are in use, and both are accepted.** Version 1 is the scaffolded default (`claude-code`, `living-docs`, `software-analysis`, `software-engineering`); version 2 marks the files that adopted the `commands:` block when COR-021 said the version bumps with it (`demo-recording`, `evidence`, `project-management`). No reader distinguishes the two — the dispatcher reads `commands:` from either — and both require the same fields, so the schema accepts `1` and `2` as an integer enum and nothing is bumped or migrated. A third value is an error until a record introduces it.
- **Known keys are strictly typed; unknown keys are errors.** Every object the schema declares is closed (`additionalProperties: false`), at the top level and inside every block, so a key the schema does not know fails the shape check at that key, with the nearest known key suggested (`unknown key 'foootprint'; did you mean 'footprint'?`) through the one renderer every backbone file schema shares (ADR-056 point 4). It fails `pkit validate` and refuses a register like any other error. The decision, and what to do about such a key, is "Strict on unknown keys" below.
- **Repository checks**, all errors but the one below: `component.name` equals the directory name; `component.version`, `requires_backbone` and every dependency range parse; every command `script` exists; a declared connection point sits under a role in `connections.roles`; an accepted data point's (and an offered event's) companion `schema` exists under the capability's `schemas/`; every command a point or extension names exists in `commands:`, and every command a validator names, every command filler a contribution names, and every resolver an anchor kind names, exists there and declares the query contract; a kind the backbone resolves itself (`path`, `record`, `artefact`) is refused at its `friction.kinds` entry; a contribution names `command` or `value`, not both; `docs.locations` paths, `friction` places, held folders and surface entries, `footprint` and `runtime_ignore` entries are relative sub-paths (no absolute path, no `..`), and every command `script` path is relative; a place's or held folder's `location` is a declared one, and a held folder names one and is no glob (a tree without the package schema gets these two from this check); an offered process point names a definition of the component (by its `id`), and its `schema_version` equals that definition's `interface.version` where the definition declares one — a difference is located at the point's `schema_version` and names both values and both files (COR-053 point 5); and the generated `depends-on` list says exactly what the component's process definitions generate, marked `generated: true` — a stale copy is located at the list (or its nearest present parent), says what is missing and what no definition declares, and names `pkit capabilities refresh <name>` as the fix (`process_dependencies.staleness`). Those last two are the repository checks that read process definitions, through one walk of the component's `schemas/` (`process_dependencies`).
- **One repository check warns**: a `runtime_ignore` entry that declares the process journals — the entry, read as a path, matches the backbone's journal pattern (`process_journal.JOURNAL_GLOB`, the one definition) — in a project that commits its journals (`process.journal.committed: true` with `enabled: true`, COR-033 point 7). The backbone owns that ignore line and drops it then, and its choice takes precedence: the render drops the component's entry too and names it in a comment line of `.pkit/.gitignore` (`JournalSettings.drops_claim`, the one rule for the render and the warning). It is the mark of a component older than the backbone it runs on, and a warning, since the render has already neutralised it; while the journals stay ignored the entry is redundant and not warned. The fix it names follows where the package comes from — its registry `origin` and the ownership module's `is_synced_copy` ("The ownership predicates" below): a `kit-shipped` package in an adopter is a synced copy the next sync overwrites, so upgrade the component together with the backbone; an `externally-sourced` one is restored to its pin (COR-041), so move the pin to an author release that drops the entry; the project's own file — an `incubated-in-repo` capability, or any package in the methodology's source — drops the entry.
- **One check across packages warns**, over the installed capabilities only: an `aliases` entry another name shadows. The dispatcher gives a top-level name to a backbone command first, then to a capability's own name, then to the first capability in manifest order that declares it as an alias; the check reads the table that walk builds (`dispatcher.installed_alias_table`, the one the dispatcher binds), so it reports exactly the aliases `pkit <alias>` does not reach. The warning is located at the entry and names the alias, its capability and what holds the name — the backbone command `pkit <alias>`, another capability's name, or the same alias of the capability that registered it first — so a generic alias (`analysis`) is never lost, or taken by a later capability, without a word. A warning, not an error: the alias is a shorthand, and the message points at the canonical `pkit <capability> …`, which still works. An alias that already reaches its own capability — its own name, or its own alias repeated — loses nothing and is not reported.
- **One check across packages fails**, over the installed capabilities only: a capability that surfaces a namespace under a name a backbone command holds. The dispatcher gives the top-level name to the backbone command, so `pkit <capability> …` runs that command and never reaches the capability. The check reads the capabilities the dispatcher builds groups for — those whose package declares a `commands:` block — against the backbone's commands as the dispatcher has them when the check runs (`dispatcher.shadowed_capability_names`), never a list kept by hand. An error, not a warning: unlike an alias, the name is the capability's canonical form. It is located at `component.name` and names the rename that lasts for where the package comes from, as for a reserved name below. The backbone gains commands with its releases, so an upgrade can take a name that was free when the capability shipped; that is why `pkit new capability` refuses such a name and `capabilities install` and `register` do not — refusing at install would make an upgrade break the installation of something that worked, where this check names the problem. A capability with no `commands:` block surfaces no namespace and is not reported.
- **One check of the registry fails**: a component registered under a name the lifecycle reserves for its kind. For a capability, `capabilities.RESERVED_CAPABILITY_NAMES` — `core`, `project`, `adr` and `backbone`, the names `pkit new capability`, `capabilities install` and `capabilities register` refuse. For an adapter, `scaffolds.RESERVED_ADAPTER_NAMES` — `backbone`, which `pkit new adapter` refuses, as `pkit init` refuses a source that ships an adapter under it: its changesets and validators would be read as the backbone's, the two places the backbone's name is read beside an adapter's. The capability-only names collide where only a capability's name is read, so an adapter may take them. One registered before its name was reserved stays registered — nothing unregisters it — so this check is where it surfaces. The error is located at `component.name`, gives the reason the refusal gives, and names the rename that lasts. For a capability it follows where the package comes from: the project's own capability is unregistered with `pkit capabilities uninstall <name>`, which keeps an authored capability's files, renamed (its directory and `component.name`) and registered again under the new name; a package a sync restores is its author's to rename, and is uninstalled until it ships under another name. An adapter, which no verb unregisters, is renamed where it is authored — its directory, its `component.name` and its entry in the backbone manifest's `components`; one a sync restores is the methodology source's to rename.
- **Another check of the registry fails**: an adapter and a capability registered under one name. The backbone reads a component by its name alone where it reads both kinds: a changeset names its component, and the release keys every `package.yaml` under `.pkit/` by name (`changesets.discover_components`), so a release would move only one of the two; every registered component's validators are owned by its name, so the two would share one owner; and the wiring resolver reads the component registry by name, so one of the two would be read under the other's kind. So the second of the two is refused wherever a component is named into a project: `pkit new adapter` refuses a name a capability holds, and `pkit new capability`, `capabilities install` and `capabilities register` a name an adapter holds — a component holds its name when the backbone manifest registers it, or when its directory exists under `.pkit/adapters/` or `.pkit/capabilities/` — and `pkit init` refuses, before writing anything, a methodology source that ships an adapter and a capability of one name. A pair registered before the refusal stays registered — nothing unregisters either — so this check is where it surfaces. The error is located at each one's `component.name`, gives the reason the refusals give (`capabilities.SHARED_NAME_REASON`), and names that one's rename, as for a reserved name above; renaming either clears both.
- **One check across packages fails**, over the installed capabilities only: a folder of held documents that oversteps its bounds ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 1) — it equals or encloses a documentation root or another declaration's place, or shares a file with its own component's place, another held folder or a rule-set folder. The error is located at the `friction.held` entry and names each bound it oversteps; it is read from friction discovery's one judgment of the folder (`friction_discovery.held_folders`), which leaves such a folder holding nothing, so its files stay artefacts of the places matching them — every held file has one holder, and rules stay artefacts (COR-051 point 2). Two components' folders sharing a file are refused at both entries.
- **One more check across packages fails**, over the installed capabilities only: an anchor kind two or more of them register under `friction.kinds` ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 2).
  - The error is located at each one's entry, naming the others.
  - No registration wins: the kind is refused for every registrant, and an anchor of it is unresolved until one registration remains.
  - It is read from the one anchor-kind registry (`friction_discovery.registered_anchor_kinds`), so what is reported is what an anchor of the kind meets.

The other checks *across* packages — roles, points, mandatory marks, cycles, fingerprints and the version relations — are the wiring resolver's ("How the wiring is resolved" below), run by `pkit validate` as its `connections` and `versions` members; `package_validate.check_wiring` is the same resolution for the pre-flight, and `resolve_active_roles` answers which roles have an active provider.

#### Strict on unknown keys

**The rule.** Package metadata is strict: a key the package schema does not know is an **error**, wherever it is written — at the top level, inside a component, a command leaf, a validator entry, a dependency, or any part of the `connections`, `docs` and `friction` blocks. [COR-053](../decisions/core/COR-053-connection-points.md) left whether unknown keys become errors to this specification, as a surface change of its own if taken (its Implications, "Schema changes"). This is that decision.

**Why now, and not from the start.** The schema shipped permissive — an unknown key only warned — while the blocks the newer records ask for were still being added one change at a time; a strict schema would have refused a package ahead of the schema knowing its block. Every block those records name is now declared: `commands` with the query-contract declaration, `validators`, `connections` (roles, extension points, and extensions with the generated `depends-on` and the mandatory mark), `docs.locations`, and `friction` places and surface. From here an unknown key is a misspelling or a key nothing reads, and every reader of the file passes over a key it does not look for — `mandatroy:` on a contribution leaves the connection optional, `foootprint:` keeps its paths out of `.git/info/exclude` — silently, which a warning beside passing checks does not prevent. Failing makes the mistake stop where it is written. It also puts the package file with the rest of the backbone's file schemas, which refuse unknown keys: the configuration file, rule sets, the filler envelope.

**What an adopter sees, and does.**

- *With only kit-shipped components, nothing.* Every shipped package validates, and the sync that brings the strict schema brings the packages with it.
- *With a package of their own* — an incubated capability (COR-031) — that carries a key the schema does not know, `pkit validate` fails under `packages`, naming the file, the key and the nearest known key (`.pkit/capabilities/<name>/package.yaml:/foootprint → unknown key 'foootprint'; did you mean 'footprint'?`), and `pkit capabilities register` refuses the capability with the same message. The fix is in the adopter's own file: rename the key to the one suggested, or delete it. A note for people belongs in a YAML comment; a new key arrives through the record that decides it and a schema release, never by writing it first.
- *A package missing a required field* — `schema_version`, `description` or `requires_backbone` — is refused the same way (`'description' is a required property`), and the fix is to add it: `schema_version: 1`, a one-line summary, a version range. The capability scaffold has always written all three.
- *A tree not yet synced* keeps its own, permissive copy of the schema, and that copy is the one applied (ADR-056 point 1), so there an unknown key still only warns — the same sentence, until the sync.

**No version bump and no migration.** The flip changes no key and no meaning: a file that carried only known keys and COR-017's fields validates as before, so the package file's own `schema_version` stays at `1` and `2` — bumping it would make every package file change for no reader's benefit. The one shipped file that had to change, the `claude-code` adapter's package (it gained its `description`), is replaced by the same sync that delivers the schema. The adopter-owned files that can now fail cannot be corrected by a script — none can know what a misspelt key meant, or write a capability's description — so the finding names the fix instead of a migration guessing it.

#### The connection, documentation and friction blocks

Three optional blocks carry what the newer core records ask a component to declare. The key names each record decides are used as written; the layout beneath them is this reference's ("Field layout and casing" lists every key). `pkit::` in the example is this distribution's publisher qualifier ("The methodology's literals", below).

```yaml
# COR-053 point 3 — roles this component provides and its connection points.
connections:
  roles: [pkit::documentation]                     # qualified, <publisher>::<role>
  extension-points:                                # points this component DEFINES
    accepts:                                       # data in (a slot, COR-052)
      pkit::documentation:reading-evidence:        # <publisher>::<role>:<point>; the role must be provided above
        schema_version: 1                          # the point's version (COR-053 point 5)
        schema: reading-evidence.schema.json       # companion under this component's schemas/
        description: What readers found on each page.   # required prose on every extension point
        combination: union                         # optional: single (the default) | union | additive
        default: { value: [], participation: alone }    # optional: always | alone
        inert: fail                                # optional: fallback (the default) | fail
        mandatory: { reason: "…" }                 # optional; the mark without a reason is refused
    offers:                                        # processes and events out
      pkit::documentation:page-created:
        kind: event
        schema_version: 1
        description: A page was written by a writing command.
        command: publish                           # the emitting command; must exist in commands:
        schema: page-created.schema.json           # payload companion under schemas/
        subject: page                              # the payload field naming the subject
      pkit::documentation:review:
        kind: process
        schema_version: 1
        description: The review process other components may depend on.
        process: page-review                       # the offered process definition's id (COR-036)
  extensions:                                      # where this component PLUGS INTO others
    contributes:                                   # data it supplies to another role's point
      - { point: pkit::analysis:glossary, schema_version: 1, command: export-glossary }   # a command filler
      - { point: pkit::analysis:audiences, schema_version: 1, value: [maintainer] }        # or the data itself
    subscribes:                                    # events it reacts to, with its command
      - { point: pkit::analysis:use-case-created, schema_version: 1, command: refresh }
    depends-on:                                    # GENERATED from process definitions' depends_on (COR-053 point 4)
      generated: true                              # the mark; a hand-written copy without it is refused
      entries:                                     # one per distinct upstream + targeted version, sorted
        - { process: pkit::analysis:use-case-review, schema_version: 2 }   # role form; the targeted interface version
        - process: project-management:issue-lifecycle                      # implementation form
          mandatory: { reason: "…" }               # copied from the definition's mark; the lifecycle reads it

# COR-049 point 4 — the sub-paths of this component's own documents, relative to a documentation root.
docs:
  locations:
    pages: { path: pages, root: user }             # root: internal (default) | user; relative sub-paths only
    spaces: { path: spaces }
    logs: { path: logs }

# COR-050 points 1, 2 and 8 — where anchored artefacts live, the documents held that are not
# artefacts, the surface that ought to be described, and the anchor kinds it resolves.
friction:
  places:
    - { location: pages, path: "**/*.md" }         # inside a declared location…
    - { path: "notes/**/*.md" }                    # …or, without one, inside the project
  held:                                            # a folder in a declared location; no place walks it
    - { location: logs, path: reviews }            # e.g. a log of reviews the component carried out
  surface: ["src/**"]                              # repository-relative globs
  kinds:                                           # an anchor kind, and the leaf that resolves it
    source: { command: resolve source }            # the leaf declares `query-contract: true`
```

`depends-on` is the one block a person never writes. **`pkit capabilities refresh <name>`** regenerates it from the `depends_on` the capability's process definitions declare (the process area README, "depends_on") and marks it `generated: true`, leaving the rest of the file as written; with nothing to generate it removes the list, and any `extensions` or `connections` block the removal empties. The schema fixes the shape and the mark; the packages pass compares the list with what the definitions generate and fails a stale copy, naming the refresh — the definition always wins; the wiring resolver reads the entries and never opens a definition; the capability lifecycle reads their `mandatory` marks ("Mandatory process connections", below). Refresh is authoring-time: it runs where the capability is authored — the methodology's source for a kit-shipped capability, the adopting project for an incubated one (COR-031) — and refuses a kit-shipped capability installed in an adopting project, whose package file is core-owned and overwritten by sync: a stale copy there is the capability author's defect, reported upstream.

#### The methodology's literals

Three names the core records need are written record-neutrally, and the literal is left to the distribution's reference ([COR-053](../decisions/core/COR-053-connection-points.md), the vocabulary paragraph of its Decision). This is that reference. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The publisher qualifier the methodology reserves for the roles it defines, written `<methodology>::` (COR-053 point 1) | **`pkit::`** | Role names (`pkit::documentation`) and point addresses (`pkit::documentation:readers`): in the `connections` block above, in the configuration file's `connections.providers` and `connections.selections` keys, and as a role block's key where the qualified form is needed. |
| The one front-matter key "owned by the methodology, named for it" (COR-053 point 10) | **`pkit:`** | An artefact's front matter, or a collection entry: the container (the schemas README, "The container"; `backbone/container.schema.json`). |
| "a sub-path the backbone owns for slot files", under the internal documentation root ([COR-052](../decisions/core/COR-052-slots.md) point 2) | **`pkit/fillers/`** | The prefix of every project filler file (the next section). |

**The qualifier names who defined a role, never who implements it** (COR-053 point 1). A third party coins its roles under its own name — `super-docs::documentation` is a different role that shares a word with `pkit::documentation` — and may also *provide* a `pkit::` role, interchangeably with the capability that first defined it, but it never coins a role under `pkit::`. Project-published roles have no qualifier yet; COR-053 leaves them to a later refinement. **The container key is not a qualifier**: an artefact has one `pkit:` key whoever published its roles, and a third party's role block sits inside it, beside the methodology's own blocks (COR-053 point 10).

These strings are this distribution's choice, not a principle: another distribution of the same records could choose others. Changing one would change files adopters have written, so it would be a surface change shipping a migration (COR-010), not a record amendment.

**Four more literals, for the commands the backbone runs.** [ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 3 leaves the literal of the query-contract declaration and the offline marker to this reference, specified with the first query commands that run — the validators [ADR-058](../../tech-docs/architecture/decisions/ADR-058-validator-registry.md) registers — the deadline of ADR-057 point 5 is named here too, and so is the declaration of what a command filler reads beyond the working tree, which [COR-052](../decisions/core/COR-052-slots.md) point 6 has its capability declare. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The one constant declaration that a command honours the query contract — bounded, deterministic, read-only, needing no network (COR-050 point 2; ADR-057 point 3) | **`query-contract: true`** | On a `commands:` leaf, beside `script` and `help`. Required on the command a validator names, on a command filler and on an anchor kind's resolver: the `packages` member reports one without it, and the runner — the validator registry, the data points' resolution, the anchor-kind registry the friction checks and rule-set validation read — refuses it. |
| The offline marker, "so a well-behaved command can tell" (ADR-057 point 3) | **`PKIT_OFFLINE=1`**, with **`UV_OFFLINE=1`** beside it | The environment of every query command the backbone starts — validators, command fillers and anchor-kind resolvers. `PKIT_OFFLINE` is what a command reads; `UV_OFFLINE` is honoured by `uv`, so a script with a `uv run --script` shebang resolves its dependencies from uv's cache and never fetches. |
| The deadline every run tells its command (ADR-057 point 5) | **`PKIT_COMMAND_DEADLINE`**, seconds since the epoch, to the millisecond | The environment of every command the backbone's runner starts — queries, predicates and the report's context read alike. A command may read it to know by when anything it starts must have ended ("A run inside a run" below). **`PKIT_COMMAND_STRAYS`**, set beside it, and **`PKIT_RUN_CACHE`**, set for the length of a `pkit validate` run, are the runner's own: no command reads or sets them. |
| Which state a command filler reads beyond the working tree — history, settled state, or both (COR-052 point 6) | **`reads:`**, a list of **`history`** and **`settled`** | On a command filler's `commands:` leaf, beside `query-contract: true`. `history` is the current history, read at HEAD; `settled` is the default branch as the backbone resolves it, never a base named for one run. Absent, the working tree only. The schema refuses any other value, an empty list and a value twice; the `packages` member, a leaf that declares it without `query-contract: true` ("How a data point resolves"). |

**How dependencies are provisioned before an offline run.** A query declares that it needs no network and runs offline-marked, so a script's dependencies must already be in uv's cache when it runs. **`pkit init` and `pkit sync` put them there**, as one of their steps (self-host included), and `pkit capabilities install`, `register` and `upgrade` run the same step for the one capability they bring in: for every command a registered component — capability or adapter — declares with `query-contract: true`, whose script carries inline script metadata (a `# /// script` block), they resolve the script's environment once, online, with uv's own resolution — `uv sync --script <script>`, which resolves the metadata and installs the environment into uv's cache **without running the script**. The step prints one line per query command:

| Line | When |
|---|---|
| `provisioned` | the script did not resolve offline, and resolved online |
| `unchanged … already provisioned` | the script resolves offline — the condition the query meets — so nothing is fetched: the step is idempotent, and a re-run resolves nothing |
| `skipped … nothing to provision` | the script declares no inline dependencies (or does not exist — the `packages` member reports that) |
| `warning … not provisioned` | the script resolved neither offline nor online — no network, no `uv` on the PATH — with uv's reason. **Never a failure**: init and sync go on and keep working offline |

A dry run asks uv nothing and prints `would provision` for each script with inline dependencies. Provisioning happens outside the bounded run: it sets no offline marker and is not bound by the command bound. A pipeline runs `pkit sync` on checkout, before its gate.

A query whose environment is not provisioned exits with uv's report that a dependency is not in its cache and the network is disabled; the query policy recognises it on standard error and names it, rather than reporting the exit: **"environment not provisioned — run `pkit sync`"** — an error finding for a validator, the reason an inert filler gives for a command filler, and distinct from a command that answered nothing.

**Two more, for recognising the methodology's source repository.** [ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md) defines the source repository as the one whose `.pkit/` is the methodology's own tree. Code that must recognise it without knowing which code runs does so by the package source beside the `.pkit/` tree at the repository root; the package's path, and the path of the dispatcher the router execs there, are this distribution's names. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The marker that recognises the source repository on the tree's side (ADR-059 point 3) | **`src/project_kit/__init__.py`** beside the **`.pkit/`** tree. The in-tree dispatcher **`.pkit/cli/pkit`** is what the router's first route execs, not a marker: a checkout whose dispatcher was deleted is still the source, and the dispatcher is reported missing | Nowhere by a project. They are read at a repository root by the entry-point router's first route (`project_kit.router.is_source_checkout`) and by the ownership predicate (`is_methodology_source`, "The ownership predicates" below). Both copies cite this table, and a test holds them equal. |

An adopter has the dispatcher but never the package source. Unlike the literals above, no project writes these, so changing them means changing the two copies together, not migrating an adopter's files.

#### How a registered command is run

The backbone runs the commands a component registers through one runner, `project_kit.command_runner` — one lookup and one bounded run, with a policy per kind of command ([ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 5; the kinds share one command runner, [COR-053](../decisions/core/COR-053-connection-points.md) point 11).

- **The lookup.** A command is a leaf of the `commands:` tree ("Field layout and casing" above), and one walk reads the tree: a command reference — a path of tokens — names a leaf through it. The dispatcher (`pkit <capability> <command>`), package validation, the validator registry, the anchor-kind registry, the process engine's predicate runner and the report builder (`pkit report`, asking the project-management capability for the workstream) all read the tree this way, so each resolves a leaf to the same script. A process predicate's `run:` names a leaf by its own name rather than its path (the process README, "The predicate runner").
- **The run.** The leaf's script is started with an explicit argument list — never a shell string — from the project root, in its own process group (inside another run, the outermost run's: "A run inside a run" below), with standard output and standard error captured: standard output is the answer, one JSON document and nothing else unless the policy reads it as text; standard error is diagnostics. The run is **bounded by thirty seconds**, a fixed backbone constant (`COMMAND_TIMEOUT_SECONDS`), not a setting (ADR-057 point 3). Exceeding it **kills the whole process group** — a script with a `uv run --script` shebang starts its interpreter as a grandchild, which killing the script alone would leave running — and an interrupt of `pkit` itself kills the group too. A run that does not start, exits non-zero, overruns, or prints anything but the answer its policy reads is never an answer; what it is instead is the policy's. Where a policy reports such a run, it names how the run ended and may show what the command wrote on standard error — never the stream whole, only its last 10 non-blank lines and at most 1500 bytes of them, every terminal escape sequence and control character removed, so a command's words can neither flood nor rewrite the operator's terminal.
- **A run inside a run.** A command the runner starts may start `pkit` again — a validator reads a point through `pkit connections resolve`, which starts the point's command filler, which reads the artefacts through `pkit friction artefacts` — and the tree keeps one deadline and one kill (ADR-057 point 5). Every run tells its command, in its environment, **`PKIT_COMMAND_DEADLINE`**: seconds since the epoch by which anything the command starts must have ended — the run's own end less two seconds, the time the command keeps to answer after something it started ran out ("The methodology's literals" above).

  A run is **nested** when it runs inside a live run: its environment carries a deadline; its process is in the process group that leads its session, as every process the outermost run's command starts is — that command leads a session of its own — and a command started from a terminal is not; and the directory the outermost run made and named in **`PKIT_COMMAND_STRAYS`** still exists, which it does only while that run's command runs. A variable left over in a shell, or outliving its run, therefore never makes a plain `pkit` nested. A nested run is bounded by the time remaining, rounded down to a tenth of a second and never more than thirty seconds — with none remaining its command is not started, and the no-answer says so — and it starts its command in the outermost run's process group rather than a session of its own, so the outermost run's kill, at its deadline or on an interrupt, reaches everything the tree started. Each level's deadline comes before its caller's, so the command that overran is the one a no-answer names, with the bound it had: when that was the time its caller had left rather than its own thirty seconds, the no-answer says so — "did not answer within the 0.4 s its caller had left" — since a caller with more time might have had an answer.

  **Strays.** A nested run cannot kill a group it shares with its callers, so when its command overruns it kills that command alone; what the command started is left to the outermost run. Each nested run keeps a marker in the outermost run's directory from just before it starts its command until the command ends by itself. One whose command overran or was interrupted, or whose own process was killed by anyone else — a `subprocess.run(timeout=…)` in a validator, the operating system's out-of-memory killer, a `SIGTERM` — leaves its marker behind. When the outermost run's command ends, however it ended, a marker left behind makes it end everything left in its group; it then removes the directory. With no marker left, nothing is swept: a group whose nested runs all ended by themselves is left as a run outside any other leaves it, so a process a command leaves running on purpose is not ended.

  **What this does not cover.** The kill reaches only the group:
  - A process that leaves the group escapes the kill: one that starts a session of its own (`setsid`) or a group of its own (GNU `timeout` without `--foreground`, a shell with job control). A `pkit` started under it runs outside the outermost group too — under a new session with the deadline it inherited, under a new group as a run of its own, with thirty seconds and a kill of its own. **In a script a query runs, do not wrap `pkit` in anything that makes a new session or group.**
  - What a killed nested command started runs on until the outermost run's command ends, not only until the nested run's deadline.
  - A marker that cannot be written — the directory cannot be written to — leaves those strays running past the outermost run's answer when it answers in time: only its own kill, at its deadline or on an interrupt, reaches them. When the outermost run cannot make its directory at all, the runs under it are not nested: each runs as a run of its own.
  - The deadline is written on the wall clock, since a monotonic clock gives two processes no reference point they can share portably; each run's own bound is measured on the monotonic clock. A clock step — a time synchronisation, the machine sleeping — between a run and one nested under it shifts the nested bound by the step, never beyond thirty seconds, and the outermost run's kill is never late.
- **A tool the backbone runs itself.** `gh`, which the landing module asks of the hosting service for `pkit pull-request` and `pkit release merge`, is not a registered command and has no answer policy: the module reads what it printed. It is started through the same runner's one bounded start for a tool (`run_bounded`): with an explicit argument list, from the directory the request acts in, with nothing on standard input, and **in the caller's process group** — never a session or group of its own, so whoever ends the group `pkit` runs in ends a `gh` in flight too. project-management runs `pkit pull-request` in a session of its own and ends that group at its bound; a `gh` request that went on after project-management had read the pull request to decide could act on it unseen. Each call is bounded by the module — a reading, a request (the CLI README, "Pull-request commands") — and on overrun, or an interrupt, the tool **alone** is ended: asked to stop, then killed two seconds later (`END_GRACE_SECONDS`), its pipes closed unread. The group is its caller's, so it is never signalled.
- **Provisioning, before any run.** A query runs offline-marked and fetches nothing, so the environment its script needs is prepared beforehand, not by the run: **provisioning is a step of `pkit init` and `pkit sync`**, which resolve every registered query command's environment once, online — and of the capability verbs that bring a capability in, for that capability's commands ("How dependencies are provisioned before an offline run" above). A query whose environment is not provisioned gives the no-answer "environment not provisioned — run `pkit sync`".
- **The policies.**

  | Policy | Run by | Arguments and environment | The answer | No answer is |
  |---|---|---|---|---|
  | predicate | the process engine, for every predicate a process definition declares | the subject and `--json`; the environment unchanged but for the run's deadline — a predicate may reach the network | a JSON object the engine interprets (the process README, "The predicate runner") | indeterminate, fail-closed: a gate stays shut — the reason naming how the run ended, with the tail of what the predicate said beside it |
  | query | `pkit validate`, for a component's validator (ADR-058) | `--json`; the offline marker set ("The methodology's literals" above) and the base override (`PKIT_CHECK_BASE`) removed — a validator answers about the project's state, never about a base named for one run (ADR-058 point 7); the leaf must declare `query-contract: true`, or it is not started | the findings document (the `validators` row above) | an error finding naming how the run ended — for an exit, with the tail of what the command wrote on standard error, its lines joined on the finding's one line |
  | query, for a filler | the data points' resolution (`project_kit.data_points`), for a contribution's `command` — read by `pkit validate` and `pkit status`, and by `pkit connections resolve` for its one point's fillers only | `--json` alone: a filler takes no parameter ([COR-052](../decisions/core/COR-052-slots.md) point 6); the offline marker set and the base override removed, whichever command started the resolution — a filler reads state, never a base named for one run (the same point); the leaf must declare `query-contract: true`, or it is not started, and a leaf that declares it reads settled state is not started while the default branch resolves to no commit ("How a data point resolves") | the filler envelope, `{"schema_version": <the point's version>, "value": <the point's value>}` and nothing else — no `remove`, which is the project's alone — whose value fits the point's schema whole | the filler inert, never an empty or a partial value: the point follows its inert policy ("How a data point resolves"); the inert reason names a run that gave no answer as the validator's finding does |
  | query, for a resolver | the friction checks and rule-set validation, for an anchor (or a cited source) of a kind a capability registers — once per anchor value for a run, and not again in it once it overran its bound ("How a registered anchor kind is resolved" below) | `--json`, the end-of-options marker `--`, then the anchor value — its one subject ([COR-052](../decisions/core/COR-052-slots.md) point 6), last, so that no value is read as an option; the offline marker set and the base override removed; the leaf must declare `query-contract: true`, or it is not started | `{"paths": [...]}` and nothing else: the files the anchor stands on, in the state the check reads | the anchor unresolved, never resolved, and never dead: the change check fails on it and its artefact is not judged (`no-answer`), and a cited source fails rule-set validation (`unanswered-source`), the reason naming the run as the validator's finding does |
  | context read | `pkit report`, for the workstream on a report's context line ([ADR-050](../../tech-docs/architecture/decisions/ADR-050-report-context-sourcing.md)) | none; the environment unchanged but for the run's deadline — the verb asks the tracker | the value it prints, read as text rather than parsed: the verb prints it bare, not as a JSON document; output that is not UTF-8 is no value | the workstream omitted — silently where the verb is absent or printed nothing; where it failed (did not start, exited non-zero, overran, printed output that is not UTF-8) the report names how it ended in a warning, with the tail of what it wrote on standard error, before going on without it |

  The report builder is bounded like every other run, not exempt: the workstream only enriches a report, so waiting on it past the bound would let a hung tracker call hold the whole report back.

  A subscriber's policy arrives with the events that run subscribers ([COR-053](../decisions/core/COR-053-connection-points.md) point 9 sets its limits).

- **The seams back: what a script reads from the backbone.** A component's script runs in its own environment and never imports the backbone. What it needs of what the backbone computes, it reads through the backbone's reading commands, each printing one stable JSON document — never by computing it again, which would be a second home for one computation (ADR-057 points 1 and 2):

  | Reading command | What it answers |
  |---|---|
  | `pkit connections resolve <address> --json` | one data point as it resolves — its value and every filler considered ("Reading one point from a script" below) |
  | `pkit friction artefacts --json` | where the artefacts are: the documentation roots, each place the project and every installed capability declares with the files it matches and the skips validation applies, every file read with its front matter's own fields, every artefact, and each folder of held documents a capability declares, with the files it holds (the CLI README, "friction artefacts") |
  | `pkit repository base --json` | settled state: the default branch as declared and resolved — its commit, or why it has none, and whether it has none yet (`unborn`) — and a comparison's base with where HEAD left it; and the history at hand: HEAD's commit, or that it has none yet (`unborn`), or why git cannot read it (the CLI README, "repository base"). A filler reads `head` for history and `default_branch` for the default branch, never `base`: no base override reaches a query, so the base it is shown is the default branch ([COR-054](../decisions/core/COR-054-default-branch.md) point 3), and the problem `default_branch` carries names no base as a fix |

  Each is read-only and needs no network, so a query may call it. The script applies the answer itself — the living-docs validator decides which of two places matching a file wins, and which space it serves — but never re-reads the declarations, lists the working tree or matches a path against a place, nor resolves a reference or computes a merge-base. The artefacts and settled-state readings resolve no data point, so a filler may call them while a point it contributes to resolves; a filler never asks for a point. A query that calls one keeps the reading inside its own bound — a filler the reading starts inherits the query's deadline and the outermost run's process group ("A run inside a run" above) — and inside `pkit validate` a point the run has already resolved is read from its run cache ("Reading one point from a script" below).

The dispatcher's proxy is not a run in this sense: `pkit <capability> <command>` is a person's focused surface, so it takes the lookup, inherits the terminal's streams, and is neither bounded nor captured.

#### How a registered anchor kind is resolved

A capability registers an anchor kind under `friction.kinds` ("Field layout and casing" above), and the backbone runs the leaf as a query ("query, for a resolver" in the policies above). [COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 2 sets the contract — the time bound, the obligations the capability declares, failing closed; [ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 3 leaves the answer's shape to this reference. The code is `project_kit.friction_discovery` (`registered_anchor_kinds`, `run_resolver`, `AnchorKinds`).

**The answer** is `{"paths": [...]}` and nothing else:

- each entry is a repository-relative POSIX path naming a file of the state the check reads — the working tree's one listing for the change check and for validation, HEAD's files for the whole-repository check and the commands that read HEAD;
- a path named twice counts once, and order does not matter;
- an empty list is an answer: the value denotes nothing, and the anchor is dead.

**Why this shape.** The engine must tell whether what an anchor denotes changed between two points — the revalidation point and now, or the change check's base and head. A resolver reads the files on disk alone: it takes one subject and cannot read the project at an older commit. So it answers where the anchored thing lives, and the engine does what it does for a record anchor: it reads those files' history from git. Nothing is stored — the friction block keeps no fingerprint and gains no field — and the resolver needs no history, no points and no knowledge of the engine.

**What the answer must name.** Every file whose content decides what the value denotes: the file or files the thing is kept in, and any file that maps the value to them — an index, a registry, a table of contents. The engine sees a change only as a change to the content of a file the answer names, so a file left out is a change nobody is asked about.

**What the engine cannot see**, whatever the answer names:

- a file that leaves the answer — one of several removed, or a mapping repointed to a file that did not change — unless a file the answer still names changed in the same commit, as a named mapping file does;
- a resolver that answers differently because its own code changed;
- in the change check, what the anchor stood on at the base.

It is also coarser than the thing itself: any change to a named file counts, as for a path or a record anchor, and a shared mapping file, once named, asks every anchor that maps through it whenever it changes. A capability keeps all of this small by its layout: one value, one file, found from the value itself (`sources/<value>.md`). Then a change to the thing is a change to that file, removing it leaves the anchor dead, and no shared file stands between a value and its file.

**How it is asked.** The leaf's script is started with `--json`, `--` and then the value, so a value that begins with a dash is read as the value and never as an option. A value the system cannot pass as an argument — one holding a NUL byte — is not started, which is no answer. The resolver reads the files on disk whichever check asks; the whole-repository check and the commands that read HEAD then read its answer against HEAD's files, so a path only uncommitted work holds is no answer there, and the report's uncommitted-paths line says how much HEAD does not hold.

**What the checks do with it.**

- The change check asks an artefact when the diff changed the content of a file the answer names — a pure rename keeps the content — its own file left out.
- The whole-repository check finds the anchor stale from the first commit after the revalidation point that changed the content of such a file, renames followed.
- The files count as anchored for the uncovered-surface measure.
- `friction.exclude` does not apply to the files an answer names: an anchor of a registered kind names what it stands on by its value, as a record anchor does, and exclusions cover paths ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 7).
- Each anchor value is resolved once per check, however many artefacts carry it. A resolver that overruns its bound is not started again in that check: the values it had left have no answer, so a resolver that hangs costs one bound, not one per value.

**Failing closed.** A resolver gives *no answer* when it exits abnormally, overruns its bound, runs in an environment not provisioned, cannot be started, prints anything that is not exactly the answer, or names a path the state the check reads does not hold. No answer is never an answer naming nothing: the anchor is unresolved, not dead, and whether what it denotes changed cannot be told.

- **A kind nothing may resolve is refused before any run:** one no installed capability registers, one two register, and one whose command names no leaf of its `commands:` tree or lacks the declaration. Its anchors are `unresolved-kind`.
- **The change check fails what it can lay at the pull request** ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 12). A resolver is asked about the head alone, so the check knows whether the diff added an anchor and whether the base could resolve its kind — the base's registrations are read from the base commit — and nothing else about the base.

  | At head | The diff | Finding | Fails in enforcing mode |
  |---|---|---|---|
  | the kind cannot be resolved | added the anchor | `unresolved-kind` | yes |
  | the kind cannot be resolved | kept the anchor, and the base could resolve the kind: the diff uninstalled the capability, added a second registrant, or dropped the declaration or the command | `unresolved-kind`, "this diff took its resolver away" | yes |
  | the kind cannot be resolved | kept the anchor, and the base could not resolve the kind either | none: the whole-repository check reports it | no |
  | the resolver names no file | added the anchor | `dead-anchor` | yes |
  | the resolver names no file | kept the anchor | `dead-unattributed`: whether the diff removed what it denoted cannot be told, and the whole-repository check reports it as dead | no |
  | the resolver gave no answer | added or kept the anchor | `no-answer`: the check could not tell whether the diff changed what the anchor denotes; a second run may clear it — if it does not, run `pkit sync`, or the resolver needs mending | yes |

  So a pull request that deletes what a kept anchor denotes passes the change check, and the whole-repository check reports the anchor dead after the merge: the third limit above, stated rather than guessed at. A missing answer is different in kind — the check did not do its work — so it fails, and a failure of that kind costs a second run.
- **An artefact with an anchor that cannot be resolved is not judged.** In the whole-repository check, `friction explain` and `friction debt`, an anchor whose kind nothing may resolve is `unresolved-kind`, one whose resolver gave no answer is `no-answer`, and either leaves the artefact's state `unresolved` — never `current`, and ahead of `stale`, though what its other anchors owe is still listed. `friction record-status` refuses it, as it refuses an artefact whose points lie beyond a shallow clone, and a reader of the machine-readable documents treats `unresolved`, and any state it does not know, as not judged (the CLI README, "Friction checks"). An anchor whose resolver names no file is dead, and its artefact is judged on its other anchors, as for a dead anchor of any kind.
- **An anchor of a registered kind can be over-broad** as a path anchor can: one whose resolver names more than half of the tracked files is warned about by the whole-repository check.

**Rule-set sources.** Rule-set validation resolves a cited source the same way (the schemas README, "Rule-set files"): a source whose resolver names no file is an error, `missing-source` ([COR-051](../decisions/core/COR-051-rule-sets.md) point 5), and so is one whose resolver gives no answer, `unanswered-source` — a resolver that ran and gave no answer has not resolved the source, and a pass nobody earned costs more than the second run a failure costs. Only a source kind with no resolver that may run is reported rather than failed.

**Provisioning.** A resolver's leaf declares the query contract, so `pkit init` and `pkit sync` provision its script as they provision a validator's ("How dependencies are provisioned before an offline run" above).

#### Where a project filler file lives: the address-to-path mapping

A project answers a data point with a file of its own (COR-052 point 2). The file's location is **derived from the point's address, never declared**, and the location rule binds the file to the backbone's filler schema by that path ([ADR-056](../../tech-docs/architecture/decisions/ADR-056-backbone-file-schemas-home.md) point 2). The mapping must be **path-safe**, because an address contains `::` and `:` (COR-053 Implications), and **injective on valid addresses**, so that no two points share a file and no path binds the wrong schema (ADR-056 point 2). This section defines it and its inverse.

**Valid addresses.** A *word* matches `[a-z][a-z0-9-]*`: a lowercase letter, then lowercase letters, digits and hyphens. A valid address is `<publisher>::<role>:<point>` with each part a word — the grammar `config.schema.json` applies to the keys of `connections.providers` and `connections.selections`. Because `:` is not a word character, a valid address splits into its three parts in exactly one way. The package schema applies the same grammar to every address a package declares ("Field layout and casing"), so every declared point has a filler path.

**The mapping.** One directory per address part, the point as the file name:

```
<publisher>::<role>:<point>   ↦   <internal-root>/pkit/fillers/<publisher>/<role>/<point>.yaml
```

`<internal-root>` is the internal documentation root: `docs.internal` in the configuration file, default `docs/`. The prefix `<internal-root>/pkit/fillers/` is a documentation location derived like any other, so COR-049's rules apply to it: a location is recorded when a command first places a document there, so that a root changed later moves nothing already placed ([COR-049](../decisions/core/COR-049-documentation-roots.md) points 4 to 6). No command places a filler yet — a project writes its filler files itself — so nothing records the prefix, and it is derived from the current root on every read (`connections.fillers_prefix`): after changing `docs.internal`, move the filler files with it. The command that writes a filler, when one ships, records the prefix on first use. The mapping fixes only what follows the prefix. `pkit/fillers/` is the backbone's sub-path, the third literal above. Its `pkit/` segment marks the folder as the methodology's among the project's own documents, as the `pkit:` key does in front matter. Because the backbone owns the sub-path, no component places documents in it (COR-052 point 2).

| Address | Path, with the default internal root |
|---|---|
| `pkit::documentation:readers` | `docs/pkit/fillers/pkit/documentation/readers.yaml` |
| `pkit::analysis:revalidation-evidence` | `docs/pkit/fillers/pkit/analysis/revalidation-evidence.yaml` |
| `super-docs::documentation:readers` | `docs/pkit/fillers/super-docs/documentation/readers.yaml` |

The first `pkit` in each path is the fixed sub-path; the second is the role's publisher, and varies.

**Why it is injective.** Let two valid addresses map to the same path. Both paths carry the same prefix and the suffix `.yaml`; removing them leaves equal strings, `p/r/q` and `p'/r'/q'`. No word contains `/`, so each string has exactly two slashes, and splitting at them gives `p = p'`, `r = r'` and `q = q'`: the same address. The argument uses a single fact, **`/` is not a word character**. As strings, then, the mapping stays injective under any word grammar that keeps `/` out, and a word containing `/` could not name a directory anyway. On disk it needs one more fact, the lower case below.

**Why it is path-safe.** Each address part becomes exactly one path segment, and the word alphabet keeps every segment ordinary:

- no `:` reaches the path — the address's separators become `/`;
- no `.`, so no segment is `.` or `..`, and the suffix's is the only dot;
- a letter first, so no segment is empty or starts with `-`;
- no upper case, so a case-insensitive filesystem cannot fold two distinct paths into one — the mapping stays injective on disk, not only as strings;
- no whitespace, quote or glob character, so a path needs no quoting in a shell or a glob.

Two limits the grammar does not rule out: a word longer than a filesystem allows for one name (commonly 255 bytes, `.yaml` included for the point), and device names Windows reserves (`con`, `nul`, `aux`, …). Neither breaks injectivity — each only makes a file impossible to create there — so a capability author avoids such words.

**The inverse.** Given a file under `<internal-root>/pkit/fillers/`: remove that prefix, require and remove the `.yaml` suffix, and split the rest on `/`. Exactly three parts, each a word, give the address `<first>::<second>:<third>`, which the mapping sends back to the same path — so the two are inverse to each other on valid addresses. Any other file under the prefix — two parts or four, a part that is not a word, `.yml` or no suffix — is not a filler: it binds to no point, and is reported rather than skipped in silence. This is the walk the location rule performs ("Filler path", ADR-056 point 2).

**Why directories rather than one file name.** Folding the address into a single name needs a separator no word contains. `<publisher>__<role>__<point>.yaml` works today, since `_` is not a word character — but its correctness then rests on a character the grammar merely happens to exclude, and a grammar that later admitted `_` would break the inverse without a trace. Folding on `-`, as `<publisher>--<role>-<point>.yaml`, is not injective at all, because `-` is a word character: `a--b-c-d` is both `a::b:c-d` and `a::b-c:d`. The directory form rests on the one separator no path segment can contain, lists fillers by publisher and by role in any file browser, and inverts by splitting, not parsing.

**What the file holds: the envelope.** The envelope is the backbone's (COR-052 point 2); its schema is `.pkit/schemas/backbone/filler.schema.json`, which is the authority (the schemas README, "Backbone file schemas"). The value inside it is the point's, judged by the companion schema of the point's active provider:

```yaml
schema_version: 1       # required: the version of the point this file targets (COR-052 point 5)
value:                  # required: the point's value, in the point's own shape (its companion schema)
  - operator            # union / additive: a list of entries — a string is its own id …
  - id: developer       # … a mapping carries a string `id`
    role: maintainer
remove:                 # optional, union / additive: removal overrides, each with its reason
  - { id: guest, reason: "No anonymous readers on this project." }
```

- **Strict.** `schema_version` and `value` are required, and any other key than the three is an error carrying the nearest known key.
- **One key for both overrides.** COR-052 names a `union` point's *suppression* and an `additive` point's *removal override*; both are the same act — drop an id, with a reason — so both are an entry of `remove`. It drops that id from every other filler, the capabilities' and the default's, before they merge; the project's own entries are its to write or leave out. A `single` point has one answer and takes no removal. A removal that matches no entry is reported as information.
- **Entries have ids.** A `union` or `additive` point's value is a list of entries, each a string — its own id — or a mapping carrying a string `id`; no id twice in one filler. The point's companion schema describes the whole list; the ids are the backbone's requirement on top of it, since merging is by id.
- **Errors the project can fix.** A file that does not parse, a malformed envelope, one targeting another version of the point, a value the point's schema refuses, a `remove` on a `single` point: each is a validation error whatever the point's inert policy (COR-052 point 2), and such a file answers nothing.
- **Inert, not wrong.** A filler whose point no active provider defines has its envelope checked and its value left alone, and is reported as inert (ADR-056 point 2). A file under the prefix whose path names no point is warned.
- **The same envelope from a command.** A command filler prints this envelope as one JSON document, without `remove` ("How a data point resolves").
- **Editor support.** The authoring command that creates a filler file stamps the editor directive at the backbone schema's path (ADR-056 point 1). None ships yet; a directive written by hand is a YAML comment, not a key.

#### How the wiring is resolved

`project_kit.connections` is the **single wiring resolver** (COR-053 point 7): `pkit validate` reports it, and the graph, the status report and the install / uninstall plans (points 7 and 8) read its `Wiring` rather than computing wiring of their own — a plan resolves the installed set plus or minus a candidate through the same function. It reads only package metadata (with the companion schemas its points name), the configuration's `connections` block, the installed versions and the envelope version of each project filler file; it runs no filler command and parses no process definition. What each data point resolves to is the layer over it ("How a data point resolves", below). It is deterministic: the same repository state yields the same wiring and the same findings, in the same order.

- **Provider selection.** One installed capability providing a qualified role is its active provider. Two or more need the `connections.providers` entry naming one; without it the role is in *conflict* — an error located at that key, with the entry to add and, once per provider, the command that writes it (`pkit connections providers set <role> <capability>`, the CLI reference's "Connections commands") — and no provider's points are defined. An installed provider that is not the selected one keeps its commands, but its points are not defined and its own extensions are inert; it is warned. A selection naming a capability that does not provide the role is the configuration pass's error (below).
- **Compatibility is an equal integer.** A contribution, subscription or `depends-on` entry binds to the active provider's point when its `schema_version` equals the point's; otherwise the counterpart is **inert**, warned, and delivered nothing. A counterpart naming a point its role's active provider does not define is warned with the points it does define. A `depends-on` entry may omit the version and binds on existence alone — an offered process point in the role form, or, in the implementation form `<capability>:<process-id>`, an offered point with that `process` id or a definition file at `schemas/<process-id>.yaml` (existence only; a definition kept under another file name is not found this way).
- **Optional by default; mandatory with a reason.** A counterpart to a role nobody provides, or to an upstream whose capability is not installed, is silent unless marked mandatory. A mark on an accepted point is unmet when nothing but the default fills it; on a contribution or subscription, when no compatible target exists; on a `depends-on` entry, when the upstream is missing or at another version. An unmet mark is an error on the side carrying it, with the fix named (meet it, or drop the mark); the capability it targets, when there is one, is warned with the carrier named — COR-030's direction split, as COR-053 point 6 applies it. Unmet marks are reported with the connections, whatever their cause.
- **Cycles.** Mandatory marks that face each other — every strongly connected group of capabilities joined by mandatory connections — are rejected, an error on each mark in the cycle: no member could be installed first. An edge is drawn only to a role's *active* provider, since which provider is selected decides whether a cycle exists; an unselected provider's marks bind nothing.
- **Fingerprints.** Two installed providers of one qualified point and version must define the same companion schema. The fingerprint is the sha256 of the schema's canonical JSON — key order and layout never count, any other difference does — compared and kept nowhere; a disagreement is an error on each provider.
- **The contributor selection.** A `single` data point — a point that declares no `combination` is one — with contributions from more than one capability needs the `connections.selections` entry naming one; without it, an error at that key.

**Version relations.** Each relation is checked deterministically and reported by functionality: the resolver's under a `versions` heading, which counts how many of each were checked and labels each finding with its relation.

| Relation | Checked | Finding |
|---|---|---|
| Backbone range | each component's `requires_backbone` admits the installed backbone version | error on the component — `[backbone range]` |
| Capability dependency ranges | each `requires_capabilities` entry names an installed capability whose version of record (its component manifest, else its package) the range admits — the order the install gate reads | error on the dependent, warning on the dependency naming each dependent — `[capability dependency range]` (COR-030) |
| Contributions and subscriptions against point versions | the counterpart's `schema_version` equals the point's | warning: the counterpart is inert — `[point version]` |
| Process connections against interface versions | a `depends-on` entry's `schema_version`, where it declares one, equals the offered process point's | warning: the entry is inert — `[process interface version]` |
| Project filler files against schema versions | the filler envelope's `schema_version` equals the point's | error at the filler — `[project filler version]`. The file sits at the path "Where a project filler file lives" gives (`connections.project_filler`); one whose envelope carries no integer `schema_version` fills nothing, and its envelope error is reported under `connections` |
| Rule-set inheritance pins | each `inherits` pin of a rule-set file against the major of the set it names (COR-051 point 7); the pins are read from the rule-set files by `rule_sets.pin_checks` (the schemas README, "Rule-set files") | error on the inheriting rule set, naming the new major — `[rule-set pin]`. A pin naming no set, or one it may not inherit, is the `rule-sets` pass's finding |
| Configuration shape against the installed backbone | the configuration file carries no version key; the configuration pass validates it against the `config.schema.json` the installed backbone ships in the tree (ADR-056 point 1) | reported under `configuration` |

A mandatory counterpart at another version is reported with the connections, as an unmet mark (above). The configuration pass checks the two selection keys against the same declarations (`connections.load_declarations`): a provider entry names a capability that provides the role; a contributor entry names a `single` data point some installed provider defines and a capability that contributes to it.

**The graph and the status report read the same wiring.** `pkit connections graph` draws it together with the process definitions' edges — `pkit process graph` is that graph's process view — and `pkit status` shows it per role and per point, the unmet marks being the ones this resolver judges (`Wiring.mark_unmet`); `pkit connections providers set` writes the provider selection after the same check the configuration pass applies. The CLI reference's "Connections commands" and "status" specify them.

#### How a data point resolves

The data kind of connection point resolves to a **value** ([COR-052](../decisions/core/COR-052-slots.md), COR-053 point 2): what the status report shows, what a project filler overrides, what contributions merge into. `project_kit.data_points` computes it as the second layer over the wiring — it reads the run's one `Wiring` and the filler files the wiring read, never resolving either again — once per run of `pkit validate`, whose `connections` member reports it; `pkit status` shows the same resolution. For each data point an active provider defines:

**The fillers, in precedence order** (COR-052 points 2 and 4):

1. **the project filler** — the file at the path the point's address maps to ("Where a project filler file lives");
2. **each contribution** of an installed capability (`extensions.contributes`), in capability-name order: its `value`, or what its command filler prints. A contribution at another version than the point's is inert (the wiring warns it); one whose capability provides a role for which it is not the selected provider is not delivered (COR-053 point 1);
3. **the definer's default** (`default.value`), as the point declares it takes part: `always` — like any other filler, at the lowest precedence — or `alone` — only when no other filler is declared: no project filler file, and no contribution to the point, in step or not, other than an unselected provider's. An `alone` default is **never promoted because a declared filler broke**.

**The policy** (`combination`, COR-052 point 3):

| Policy | The value | Collisions and overrides |
|---|---|---|
| `single` (also when none is declared) | the answer of the first filler in precedence order that answers; the others are not asked, and a command filler not asked is not run | among several contributions, the contributor selection (`connections.selections`) picks one; several with none selected leave the point unresolved — the wiring's error at the selection key — unless the project filler answers, since it precedes them all; the default never stands in for a choice nobody made |
| `union` | a set: every answering filler's entries merged by id, listed by id | a project entry replaces a capability's or the default's entry with that id **whole**, never field by field; a capability's replaces the default's; two capabilities supplying one id is an error until the project settles it — an entry of its own with that id replaces both, or `remove` drops it |
| `additive` | a list: every answering filler's entries, in precedence order — the project's, each capability's, the default's | any id supplied twice is an error, the project's included: nothing overrides; an entry leaves only through a removal override, and the project may then supply its own under that id |

**Choosing entry ids.** A point's definer chooses an id that identifies what one filler alone can say. Where several fillers can each report on one subject, the id carries a part the filler names, opening with the filler's own name, so their entries stand side by side and only a real double claim collides. One filler never supplies an id twice, so that part is as fine as one entry.

`remove`, the project filler's removal overrides, drops each id from every other filler before they merge, and each carries its reason ("Where a project filler file lives"). A collision leaves the point unresolved: a gate never reads one of two entries picked by accident.

**Command fillers, and the parameter rule.** A contribution's `command` is a query (COR-052 point 6; ADR-057 point 3). It **takes no parameter**: a data point is a value, so a question that needs an input — which documentation one change owes, say — is not a data point but a process point, whose predicates take the one subject; the need is met by a parameterless point listing the obligations, which the gate applies to the change, or by a process point whose subject is the change. The command runs under the query policy of the one runner ("How a registered command is run"): its `commands:` leaf must declare `query-contract: true` — the `packages` member reports one without it, and it is never started — then it is run from the project root with `--json` alone, the offline marker set and the base override (`PKIT_CHECK_BASE`) removed, whichever command started the resolution, in its own process group, bounded by thirty seconds — or, when the point is read inside another run, by what remains of that run's bound, in the outermost run's process group ("A run inside a run") — and prints one filler envelope, `{"schema_version": <the point's version>, "value": <the point's value>}`. An abnormal exit, a timeout, output that is not exactly that envelope, an answer at another version or carrying `remove`, or a value that does not fit the point's schema whole is **no answer** — never an empty and never a partial one: the filler is inert. Needing no network is declared and trusted, not enforced (COR-050 point 2; ADR-057 point 4); the status report shows, for each command filler, whether its command declares it.

**What a command filler reads** (COR-052 point 6). A filler reads state, and never a base named for one run: the working tree, the current history, and — of settled state — only the default branch, as the backbone resolves it ([COR-054](../decisions/core/COR-054-default-branch.md) point 2), whatever branch a change targets. A base named for one run belongs to a comparison: a value that followed it would be answered per run, a parameter by another route. Nor does a filler compare the branch at hand with settled state — that answers about a change, a process point's question or the consumer's work.

- **The declaration.** Beyond the working tree, a filler's `commands:` leaf declares what it reads: `reads: [history]`, `[settled]` or both ("The methodology's literals"); absent, the working tree only. It is declared and trusted, as the query contract is: the filler reads history and settled state through the backbone's reading commands — `pkit repository base --json`, its `head` for whether there is history (HEAD's commit, none yet, or why git cannot read it) and its `default_branch` for the default branch, never its `base` — resolves no reference itself and does not compare the branch at hand with settled state. A `reads` this reading does not understand is the `packages` member's error, and the filler is not started.
- **What the backbone enforces.** No base override reaches a filler, whichever command resolves the point — `pkit validate`, `pkit status` or `pkit connections resolve`. HEAD, whether the clone is shallow, and the default branch are read once per resolution, when a filler first declares `reads`. A filler that declares `settled` is **not started** while the default branch resolves to no commit for any reason but having none yet — a remote holds it and this clone has not fetched its copy, or the declared name names no branch here: it is inert, with the reason naming the fetch (`git fetch origin <default-branch>`) and the declaration as the fixes, never a base, and the point's inert policy decides the rest — an error under `fail`, a warning under `fallback`.
- **Empty is an answer; unreachable is none.** State that does not exist yet holds nothing, and the filler answers with an empty value: a repository with no commit — HEAD a branch before its first commit (`unborn` in the reading's `head`) — or a default branch nothing has been committed to — no remote, and HEAD that branch before its first commit (`unborn` in its `default_branch`) — which starts the filler. State that exists and cannot be reached from this clone gives no answer, never an empty one: a commit git cannot read here is such state, never a repository with none. Where a remote exists and this clone has no copy of its default branch, a branch never pushed looks the same as one not fetched, so the backbone treats both as unreachable and refuses — a filler that declares `settled` is inert there until the branch is first pushed or fetched. Only the filler knows how much history it needs, so a history a shallow clone cut short of it is the filler's to detect, and it exits non-zero.
- **What the reports name.** For each command filler that declares `reads` and was asked, the state it declared and the commit it was read at, since its answer depends on what the clone has fetched (COR-052 point 7): the `connections` member of `pkit validate` adds one line per such filler taken or inert — `<address>: <capability> (command '<ref>') reads history (HEAD <sha12>[, shallow clone])`, `… reads the default branch (<ref> at <sha12>)`, joined with `and` when it reads both, and `(HEAD, no commit yet)` or `(<name>, no commit yet)` where there is none yet, `history (git cannot read HEAD here)` where HEAD names a commit git cannot read, and `the default branch (it resolves to no commit here)` for a filler not started because the default branch cannot be read — the status report appends the same to the filler's line, and `pkit connections resolve --json` carries it as each filler's `reads`.

**The inert policy** (`inert`, COR-052 point 6). A filler meant to answer that cannot — its version differs, its command gave no answer, its value does not fit — is inert:

- `fallback` (also when none is declared): the point resolves from the fillers that remain, with a **warning** naming the inert one; if none remains, it is unresolved with the warning;
- `fail`: the **whole** point is unresolved, whatever its policy, with an **error** naming the inert filler — the policy a point that feeds a gate, a check or validation declares, so a gate never passes on the entries that happened to survive.

A defect of the project's own filler is an error whatever the policy (above), and that filler answers nothing; its error is the one finding, and the point follows its inert policy for what remains.

**What `pkit validate` reports, under `connections`.** A count line — data points defined, resolved and unresolved, and project filler files — then a line per command filler that reads beyond the working tree ("What a command filler reads"), then the findings:

| Severity | Finding |
|---|---|
| error | a project filler that does not parse, a malformed envelope, a value its point's schema refuses, a `remove` on a `single` point (the envelope at another version is the `versions` member's `[project filler version]`); two capabilities supplying one id to a `union` point, any collision in an `additive` point; an inert filler of a `fail` point |
| warning | an inert capability filler or default of a `fallback` point (an out-of-step contribution is the `versions` member's warning, not repeated); a file under the fillers prefix that names no point; a point whose companion schema cannot be applied, which does not resolve |
| info | a removal override that matches no entry of the other fillers |
| report | a project filler whose point no active provider defines: inert, its envelope checked, its value not read |

A filler command lacking the declaration, a `reads` on a leaf without it, or a contribution naming both `command` and `value`, is the `packages` member's error.

**What `pkit status` shows** (COR-052 point 7), under "Data points": where the project's filler files live and how many there are; how many points are defined, resolved and unresolved; then per point its policy, inert policy and default participation, and whether it resolved or why not; its value — a `single` point's answer with the filler that gave it, or each entry of a `union` or `additive` point with its origin and what it replaced; each removal override with its reason and the fillers it removed from; and every filler considered — `taken`, `inert` or `passed over`, with the reason — a command filler saying whether its command declares the query contract and, once asked, what it read beyond the working tree and at which commit.

**Reading one point from a script.** `pkit connections resolve <address> --json` prints the same resolution of one point as a stable document (the CLI README, "Connections commands"). It is how a component's own script reads a point it defines — a capability script runs in its own environment and does not import the backbone — before applying the value itself: the consumer, not the point, knows what the value is applied to. **A consumer dispatches on `outcome`, never on `why`.** The document says how the resolution ended as one value from a closed set — `resolved`, `unfilled`, `collision` and the rest the CLI README lists — and `why` is that ending's sentence for people, whose wording is no contract. The filler states alone cannot tell the endings apart — a point that does not resolve lists every filler that answered as `passed over`, so a collision looks like a point nothing fills — and a consumer that turns a rule off when nothing fills the point reads `unfilled`, not the absence of a taken filler. A value it does not know means it could not tell how the point ended: never `resolved`, never `unfilled`. **It resolves that point alone**: only its fillers are asked, so no other point's command filler starts, and reading one point costs what that point costs, however many others the project has. `pkit validate` and `pkit status` still resolve every point. Within one run each point resolves at most once, whichever reader asks first, sharing the run's one wiring and filler files. Points never read one another, so a point resolved alone is the point resolved among all. **A run of `pkit validate` spans processes** — a capability's validator reads a point through this command — so it keeps what it resolved in a **run cache**: a fresh temporary directory, named in the environment of every command the run starts (**`PKIT_RUN_CACHE`**) and removed when the run ends; when no directory can be made, the run goes without one and every reader resolves for itself. Only a process of the run uses it — the one that opened it, or one running inside a live run ("A run inside a run") — so a variable left over in a shell is ignored, and a `pkit validate` started there opens a fresh one. Each point resolved in the run is written there with the findings its resolution made and the bound it was resolved under: an entry records the resolution its first asker made, within the time that asker had. A resolution in which a command filler gave no answer for want of that time — it overran the time its caller had left, or had none left to start in — is not written: a reader with more time might get an answer, so the next reader resolves the point itself. For a point already there, `pkit connections resolve`, inside the run, prints the point from it without resolving anything — not even the wiring — and says so, `"from": "run-cache"` in its document; otherwise it resolves the point, writes it there, and says `"resolution"`. Whichever process of the run asks first resolves a point, so its command fillers run once per validate however many validators read it — again only after an asker ran short of time.

#### Discovery: what a capability would connect to

A capability's connections are readable without installing it, and what an install or an uninstall would change in the wiring is known before it happens ([COR-053](../decisions/core/COR-053-connection-points.md) point 8). `project_kit.capability_plans` computes all of it from the one resolver ("How the wiring is resolved") and resolves nothing of its own (ADR-057 points 2 and 6). The commands are in the CLI reference, "Discovery".

**The local catalogue.** Where a capability not yet installed is found: the capabilities registered in the project (read from their installed tree), capability subtrees authored in the repository at `.pkit/capabilities/<name>/` and not registered (incubated, COR-031), and the capabilities that ship with the running pkit — its kit source, the tree installed with the tool. A name in more than one place is read from the first, in that order; where the repository's `.pkit/` *is* the kit source, an unregistered capability there is kit-shipped. All three are on disk: nothing is fetched to read a capability, to plan for it or to suggest it (`capabilities.local_catalogue`).

**`show`.** From the package metadata alone — `connections.roles`, `extension-points`, `extensions` — as the resolver reads them (the same parser, descriptions included), and what would connect here: the live wiring's bindings to and from an installed capability; for one not installed, the bindings of the wiring the resolver computes with it added.

**A plan is exact because it runs the resolver.** `connections.resolve_wiring_with` is the live resolution over the installed set plus or minus one capability; everything else — the selections, the installed backbone version, the project's filler files — is read from the tree as the live wiring reads it. A candidate is read where it is (its companion schemas, its definitions) and located where the operation will put it (`.pkit/capabilities/<name>/package.yaml`), with the version its package declares — the version install stamps and register reads — and it comes after the installed components, where install appends it to the registry. The plan is the difference between the live wiring and that one, in terms that do not depend on where anything was read: the roles whose answer changes, the points defined and no longer defined, each counterpart whose status or answering capability changes, and the findings added and resolved (located relative to the project root). The wiring the operation then leaves differs from the one before it by exactly that difference; a test runs the plan, runs the operation, and compares, for install and for uninstall.

| Plan | Lists |
|---|---|
| Install (`install --plan`) | the connections it would make, and those it would break; each role conflict it would open, with the provider-selection command that resolves it, one per provider (`pkit connections providers set <role> <capability>`); what the capability needs — the errors the install would put on the capability's own package: an unmet mandatory mark, a mandatory cycle, a backbone or capability range the project does not meet; the role blocks whose meaning changes — an orphaned block the new provider adopts, a bare key a second active role would make ambiguous (COR-053 point 10, "Keys"; rewriting it is the project's, with consent) |
| Uninstall (`uninstall --plan`) | the fillers lost — its contributions, with whether each point stays filled, is left unfilled or is no longer defined, and the project filler files answering a point it defines that no provider would define after it, kept and inert; the processes left without a provider (`depends-on` entries it answered) and every other counterpart left without one; the artefacts whose role blocks would be orphaned — preserved and reported, never an error; the selections in the configuration left naming it |

Both then list the roles, points and findings that change. A plan writes nothing and runs no filler command — the resolver resolves wiring, not data (COR-053 point 7). What it does not predict, stated: the role blocks it judges are those of the artefacts in the places declared now, so a place the operation adds or removes is not walked in advance; rule-set pins are relations between rule-set files, not connections, and are left out of the difference.

**Suggestions — a suggestion is never an action.** Where the live wiring has an unmet need — a data point filled by nothing but its default, a role an installed counterpart targets and no installed capability provides, an implementation-addressed upstream not installed — the status report names each capability of the local catalogue not installed whose package would answer it: a contribution at the point's version, the role among its roles, the upstream by name. Read from package metadata on disk only; never fetched. It is text: the capability, why, and `pkit capabilities show <name>` — nothing is installed, selected or written. `capability_plans.suggestions` is their one computation, which any view of the wiring reads rather than suggesting on its own.

## The component registry

The backbone manifest's `components` list is the canonical install record.

**Install** a component → run the pre-flight checks (see below), create its per-component manifest at the designated path, then append a `{kind, name, manifest}` entry to `components`.

**Register an in-repo (incubated) capability** (COR-031) → a no-copy variant of install for a capability the adopter authored in its own repo. Run the same pre-flights *except* "exists in kit source" (the in-repo tree *is* the source), then append a `{kind, name, origin: incubated-in-repo, manifest}` entry — **no subtree copy, and no kit-written per-component manifest** (the tree is adopter-owned; COR-031 D2/D3). Deploy primitives and dependency gating run identically to install (COR-031 D1) — only source-reconciliation differs (below).

**Remove** a component → run refusal checks (see below), delete the registry entry, then delete the per-component manifest file. Adopter-owned content authored on top of the component (project-side records, customisations) is left untouched per COR-005 and the no-shared-files invariant. For a **capability**, whether the capability's *subtree* is also deleted is origin-dependent — a kit-shipped copy is deleted, an incubated (adopter-authored) subtree is kept unless explicitly purged (COR-031 D4; see "Uninstall: origin-aware removal" below).

**Status / validate / upgrade** walk the registry to find component manifests, then operate per component.

### Install pre-flight checks

Before placing files, `pkit capabilities install` runs five checks in order. `--plan` runs after the first — an installed capability has no install plan — and stops there, writing nothing: what the backbone, dependency and mandatory-connection checks would refuse on is among what the plan says the capability needs ("Discovery: what a capability would connect to").

1. **Already installed?** Refuse with a hint to use `upgrade`.
2. **Backbone compatibility** — the capability's `requires_backbone` range must include the current backbone version. This is the shared backbone-satisfaction gate (COR-007 pattern-extraction): the *same* check runs from both capability-entry paths — `install` (kit-source copy) and `register` (in-repo incubated) — so neither path can activate a capability the current backbone cannot support.
3. **Capability dependencies (COR-030)** — every entry in `requires_capabilities` must be satisfied: the declared dependency is installed *and* its recorded version falls within the declared semver range. Refuse with an actionable hint naming what to install or upgrade first. Never auto-installs.
4. **Mandatory process connections (COR-053 point 6)** — every `depends-on` entry the capability marks mandatory must find its upstream, at an equal interface version when it names one. Refuse, one line per unmet mark with its reason ("Mandatory process connections", below). Never auto-installs.
5. **Naming collision detection** — skills/agents from the new capability must not collide with already-installed names. Interactive resolution available.

**In the methodology's source repository, run by its own code** ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)), the capability's subtree lies in the tree the running code installs from (`capabilities.authored_in_source`): the source is the destination. Install then places no files: after the first four checks it registers the capability in place with origin `kit-shipped` — no copy, no per-component receipt, no `project/` stub — and deploys it. Its collision check is register's (the capability's own artefacts are not collisions against themselves), and a collision with other content is refused, since nothing is copied that could be skipped. Beneath the verbs, a capability copy whose source and destination are one tree is refused for any caller.

### Register pre-flight checks (incubated; COR-031)

`pkit capabilities register` shares the install pre-flights that still apply (backbone-satisfaction, capability-dependencies, mandatory process connections, collision detection against *other* installed content) and skips "exists in kit source" (the in-repo tree *is* the source). It adds one check the install path doesn't need:

- **Self-consistency validation (COR-031 D1)** — the adopter hand-authored this capability; nothing upstream validated it. Before activation, its own `package.yaml` (run through the same package validator `pkit validate` uses — the schema and the repository checks in "Validation" above; only its errors refuse — an unknown key among them, "Strict on unknown keys" above), required layout (`README.md`), and own schema pairs (validated by the same validator `pkit schemas validate` runs) are checked against the working tree, which is its spec. Refuse with the structural problems listed. This is *self-validation*, not source-reconciliation — origin suppresses the latter (below), never the former.

### Uninstall: origin-aware removal (COR-031 D4)

`pkit capabilities uninstall` first runs three refusal checks (all defeatable by `--force`); `--plan` runs before them and stops there, writing nothing ("Discovery: what a capability would connect to"):

1. **Declared dependents (COR-030)** — if any installed capability lists this one in its `requires_capabilities`, refuse and name the dependents. The operator must uninstall or upgrade the dependents first.
2. **Mandatory process connections (COR-053 point 6)** — if the removal would leave another capability's mandatory `depends-on` mark unmet, warn, naming each counterpart with its mark's reason, and refuse; under `--force` the warning is still printed and the removal proceeds ("Mandatory process connections", below).
3. **Textual references** — if any adopter-authored file cites the capability (citation token or path reference), refuse and list the references.

Once those pass, **what gets deleted depends on origin** — origin-blind deletion would destroy adopter-authored work, the exact hazard COR-031 exists to prevent:

- **`kit-shipped`** — the subtree is a disposable copy of kit source. Uninstall deletes the subtree, removes the registry entry, and re-runs deploy (deploy's stale-removal pass then drops the harness symlinks, since the source is gone). Unchanged from before.
- **`incubated-in-repo`** — the subtree is the adopter's *only* copy of authored work. Uninstall **unregisters in place**: it removes the registry entry and drops the capability's deployed harness skills/agents, but **leaves the authored subtree on disk** (the CLI reports "unregistered in place; your authored files are kept at `<path>`"). Because the adapter's agents deploy keys stale-removal on whether the *source file* still exists — and here it does — a deploy re-run would not drop the agents (the skills deploy reads the registry and would drop the skills), so the lifecycle runs each installed adapter's **undeploy primitive**, `undeploy-capability.sh <name>`, found by name as the deploy primitives are (the adapters README, "Primitives the lifecycle calls"). The adapter removes what it deployed for that capability; the lifecycle names the capability and carries no harness path. An adapter that ships no undeploy primitive is named in a `warning` line — its harness still carries the capability — never skipped silently. The undeploy runs before the registry entry is removed, so a failing adapter leaves the capability registered and the uninstall re-runnable. Deleting an incubated capability's files is a separate explicit opt-in: `--purge` (which confirms first, honouring the pause-before-destructive-ops discipline; `--yes` skips the prompt for non-interactive use). The default never deletes incubated files.
- **The methodology's source repository, run by its own code** ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)) — whatever the origin, the subtree is the capability's source, never a copy, so it is never deleted: it is unregistered in place as an incubated one is, the adapters' undeploy primitives included. For a `kit-shipped` registration, whose uninstall would otherwise delete the subtree, the CLI first says which subtree it would have deleted and that it unregisters instead, and asks (`--yes` answers, `--dry-run` asks nothing). `--purge` is refused; a capability leaves the source through git. The guard sits in `capabilities.uninstall_capability`, which resolves the running code's tree itself, so no caller deletes the source. Run by other code, uninstall refuses there before anything else, as install, upgrade and register do.

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

### No path down: an older pkit refuses (#1212)

The target of a backbone upgrade, and the content a sync writes, is the running pkit's own version: a release's content is tied to its code (ADR-033). That version can be *older* than the project. A pin raise leaves the installed tool where it was, and when the entry-point router cannot fetch a project's pin it runs the installed tool instead (ADR-039). So before either writes anything, `upgrade` and `sync` compare the running version with the project's recorded content version (`backbone_version` in the backbone manifest) and with its pin (`.pkit/version-pin`), if there is one:

- **The content or the pin is newer than the running pkit:** refuse. Exit non-zero, name the versions and how to get the right pkit, and write nothing: no content, no manifest, no pin. Without the refusal, sync would write the older content over the newer and upgrade would also move the pin down. Migrations are forward-only (COR-010) and a pin is never moved down (ADR-049), so there is no path down to take; a project is rolled back with git (`git checkout <ref> -- .pkit/`), which restores kit-owned and project-owned state together. No flag overrides the refusal, `sync --force` included, and a dry run refuses too.
- **Both are at or behind the running pkit:** proceed as the steps above describe.

Only an unambiguous order refuses, as with the capability guard below: a recorded version that is absent or not valid semver is not compared, so a corrupt `backbone_version` is one sync repairs and a pin that is not a version blocks nothing. Read-only commands are unaffected. In a pinned project's `upgrade`, the check comes after the branch that runs as the pin's own code and auto-advances the pin, because that branch is how content left ahead of its pin by an interrupted raise is recovered.

The CLI README's `sync` entry carries the operator-facing detail: the refusal's remedies and the router's notice when it runs a pkit older than the pin.

### Per-component upgrade

Upgrading just one component (e.g., the project-management capability) skips backbone-side steps as long as the component's new version remains within `requires_backbone` of the current backbone. The same compatibility check from step 1 gates entry. Steps 4 (component migrations), 5 (component-scoped reconciliation), and 6 (component manifest version bump) run; step 2 pulls only the component's source.

#### Upgrading an incubated capability (COR-031 D1/D4)

`pkit capabilities upgrade <name>` is **origin-aware**. For an `incubated-in-repo` capability there is no kit source to resolve against — the working tree *is* the source — so the command **must not** route through the kit-source resolution path. Doing so would mislabel the capability "no longer ships from source" and steer the adopter toward the destructive uninstall. Instead, "upgrade" for an incubated capability **re-applies deploy from the in-repo tree** (mirroring the sync skip-branch below): any newly-authored skills/agents re-materialise in the harness, and source-reconciliation stays suppressed. If the in-repo subtree has gone missing, the command reports that plainly — never as a kit-source orphan, and never suggesting uninstall. A `kit-shipped` capability's upgrade path is unchanged (resolve from kit source, refresh, run migrations).

In the methodology's source repository, run by its own code ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)), a `kit-shipped` capability's kit source *is* its subtree, so its upgrade re-applies deploy in place the same way: the deploy primitives re-run and its query commands are provisioned, with nothing copied, no receipt restamped and no migration run — migrations carry an adopter's copy forward, and there is no copy. It is sync's self-host path for one capability.

For capabilities, a **direction-split dependency check (COR-030)** runs before collision detection:

- *Upgrading a dependent* — the new source version's `requires_capabilities` is checked against the installed dependency versions. If a dependency is absent or out of range, the upgrade **refuses with an actionable hint** (the operator controls the dependent version; no deadlock).
- *Upgrading a dependency* — installed capabilities that declare this capability in their `requires_capabilities` are checked against the new version. If the new version falls outside a dependent's declared range, the upgrade **warns loudly and requires `--force` to proceed** — it is not a hard block. A hard block would deadlock (the operator cannot advance the dependency without cascade-upgrading the dependent, which is out of scope per COR-030). Use `--force` as the by-hand analogue of cascade-upgrade, then upgrade the now-desynced dependents to restore consistency.

Both entry points — backbone-wide `pkit upgrade` and single-capability `pkit capabilities upgrade <name>` — share one version-range / installed-state predicate (`capabilities.check_capability_dependencies`). The backbone-wide path does not move capability versions, so only the "dependent against unsatisfied dependency" direction (refuse) applies there; the warn+force direction applies only in the single-capability path.

#### Mandatory process connections (COR-053 point 6)

A capability's generated `depends-on` entries may carry a mandatory mark (the process area README, "depends_on"): the upstream process definition must exist — offered at an equal interface version when the entry names one. The lifecycle is the mark's **one reader**, and it reads the mark from package metadata only, never by parsing process definitions (validation keeps the list fresh against them). It judges through the wiring resolver ("How the wiring is resolved"), over the wiring the operation would leave — the installed set with the capability in place of any installed copy, or without it — so a mark refuses exactly when `pkit validate` would then report it unmet. The disposition is COR-030's direction split:

- **The side carrying the mark is refused.** `install`, `register` and `capabilities upgrade` refuse a capability whose mandatory upstream would be missing — its capability not installed, no installed capability providing its role, or no such process offered or defined — or offered at another interface version, one line per unmet mark with the mark's reason, and the hint to install or upgrade the upstream first. There is no override: the operator chooses which version of the carrier to install, so nothing deadlocks.
- **The side the mark targets is warned.** `capabilities upgrade` and `uninstall` of a capability name every other capability whose mandatory mark the operation would leave unmet — met, or at least not already unmet, before it — and refuse unless `--force` is passed; under `--force` the warning is still printed and the operation proceeds. A mark that was unmet before is not the operation's to report. Never a hard block: a hard block could deadlock.

Two marks facing each other — each capability's mandatory connection needing the other installed first — are a cycle no install order satisfies; validation rejects it and the install plan reports it (COR-053 point 6). The backbone-wide `pkit upgrade` does not run this gate: it moves every kit-shipped capability at once, and `pkit validate` reports any mark the upgraded tree leaves unmet.

## Reconciling derivable state

Two commands consume the manifests differently for the same conceptual job — "is reality consistent with the spec at the recorded version?":

- **`validate`** computes the expected state for derivable resources at each recorded version + adopter's config, compares to actual reality, reports drift. Manifest-tracked resources are compared directly: manifest entries vs. backend.
- **`upgrade`** does the same comparison, then *applies* changes to bring reality into line (step 5 of the flow).

Either way, the kit-side spec at the recorded version is the source of truth for what should exist; the manifest tracks only what the spec can't recover (recorded version, opaque IDs).

### The incubated-origin skip-branch (COR-031 D1)

The reconciliation above assumes a kit-side spec to reconcile against — true for a `kit-shipped` capability, false for an `incubated-in-repo` one, whose working tree *is* the spec. So `sync` (and the capability-refresh inside it) **skips source-reconciliation for any capability whose registry `origin` is `incubated-in-repo`**: it does not re-copy from kit source, and it does not emit the "no longer shipped from source" orphan warning that a kit-shipped capability missing from source would trigger. The capability's adopter-owned files are left exactly as authored — the no-shared-files invariant (COR-001) applied to incubated content.

The skip is scoped to *reconciliation against the kit source only*. Everything else is unchanged: deploy primitives still run (the capability's skills/agents re-materialise in the harness), dependency gating still counts the capability as installed, and structural self-consistency validation still applies against the adopter's own tree (which is its spec). Origin governs source-reconciliation, not participation or self-validation.

One boundary case (COR-031): if a same-named capability *now* also ships from kit source — graduation arriving before graduation is specified — `sync` surfaces the collision rather than silently shadowing either tree, so the adopter can decide. The default skip applies only while no kit capability of that name exists.

### The downgrade guard on capability refresh (issue #524)

The `kit-shipped` refresh above copies the source subtree wholesale. On its own that is direction-blind: a source *older* than the installed version would overwrite newer committed state with stale content — the exact data loss reported in #524, where a mis-pinned source refreshed an installed capability back several minor versions. So before refreshing a `kit-shipped` capability, `sync` compares the **source** version to the **installed version of record** (the per-component `manifest.yaml`, falling back to the installed `package.yaml` — what the refresh would actually overwrite):

- **source version < installed version (a downgrade):** refuse this capability's refresh, print a `refused` line naming both versions, and leave the installed tree untouched. `sync --force` overrides — the downgrade proceeds, but a loud `downgrade` line records the deliberate overwrite. Under `--dry-run` the refusal is *previewed* (not a "would refresh") so the plan is honest.
- **source version ≥ installed version:** refresh as before.

The guard is defence in depth, orthogonal to *why* the source is stale, and fires only on an unambiguous downgrade — an absent or unparseable version on either side is treated as "not a downgrade" so an unreadable manifest never blocks a routine sync. It is scoped to the `kit-shipped` refresh branch: the incubated skip-branch above is unchanged (no kit source to compare against), and the "no longer ships from source" orphan case is likewise untouched. It is the per-capability guard under a whole-project one: before any capability is reached, sync has already refused a running pkit older than the project's content or pin ("No path down" above), a refusal `--force` does not override.

### The ownership predicates (`ownership.py`)

The tier map above — which trees the kit owns, which are the project's, and how a capability's `origin` changes the answer — is also a question *other* layers need to ask. `.pkit/lifecycle/ownership.py` answers it as `is_sync_managed(target_root, path)`, and every consumer imports that one definition.

It answers a **second, narrower** question beside it: `is_adopter_owned_by_tier(rel_posix)` — *does this `.pkit/`-relative path sit on the project side of the no-shared-files split, by tier alone?* The two are not interchangeable, and picking the wrong one is a real error. `is_sync_managed` additionally consults a capability's **registration** (an unregistered or `incubated-in-repo` capability is not sync-managed whatever its tier) and reads everything *outside* `.pkit/` as unmanaged — so `src/`, which legitimately ships, answers False. A caller asking "may this be distributed?" needs the tier predicate; a caller asking "is this the kit's to manage, so an agent may not claim write authority over it?" needs `is_sync_managed`. Note what that second question is **not**: `pkit sync` does not call it. Sync decides what it writes through the copy path's own ownership handling, so a wrong answer here cannot overwrite an adopter's file — it can only misplace write authority. The name invites the other reading, and #823 was filed on exactly that misreading. Pass **`is_adopter_owned_by_tier`** a file path: its depth-free `project/` case reads every part except the last, so a directory path naming the tier itself (`agents/project`) answers False — though its other cases do match on a final component, so this is a rule about that case rather than about the whole predicate. `is_sync_managed` is deliberately the other way: it matches the declared tier positions by *prefix*, so the tier directory itself answers "the adopter's" — its consumer passes overlay entries, which are usually directories. "Is this *directory* the adopter's tier?" is a different question, and the packaging hook declares its own answer rather than asking this predicate.

It lives here rather than in the CLI package for the reason [ADR-003](../../tech-docs/architecture/decisions/ADR-003-permission-core-code-home.md) records for the permission decision core: an adapter's deploy primitive runs **in the adopter's tree**, where the globally-installed `pkit` runtime is not importable. Propagated in-tree code is the only home both the CLI and a propagated adapter script can reach, so the area is propagated and the module ships with it. Dependency direction is inward — the CLI imports it, each adapter imports it, and it imports neither.

`is_sync_managed`'s first consumer is the agent-overlay write-authority check ([ADR-051](../../tech-docs/architecture/decisions/ADR-051-process-author-edit-authority.md)): a *write-carrying* overlay category may not name sync-managed content, which is the no-shared-files invariant applied at the agent surface. The module also declares that category set (`WRITE_CARRYING_CATEGORIES`), beside the predicate that guards it. Re-deriving either per adapter would fork the ownership rule and silently skip the check on the next harness, so a test fails any adapter script that carries a copy.

`is_adopter_owned_by_tier`'s consumers are the packaging build hook (`hatch_build.py`) and the test that holds it honest — plus one expression of the rule that deliberately does not call it: the sdist's `withhold` globs, a build-hook option in `pyproject.toml` that mirrors the same cases by hand. The hook could apply the predicate to the sdist as well; it does not, so that the sdist's filter stays independent of the wheel's and the test comparing the two artifacts can catch a hole in the predicate. That copy is the one to check first when the two distributions disagree. The wheel bundles the methodology tree by force-include, and hatchling's `exclude` cannot filter force-included paths — so the manifest carried its own idea of which paths were adopter-owned, **disagreed with this module, and nothing could notice**: 51 adopter-owned files shipped, including git-ignored runtime state that made the artifact depend on the build machine. Deriving the boundary from this predicate is what closes that, and it is the same lesson ADR-051 records one altitude down — a second copy of an ownership rule forks silently.

`is_sync_managed` is deliberately **conservative under `.pkit/`**: anything the map does not recognise as project-owned reads as sync-managed. A false "not managed" would hand out write authority over kit content, which is the costlier direction and why the bias points this way. But the cost of a false "managed" was understated here as "a rejected overlay entry the adopter re-points": when the misjudged path is the adopter's *own* file, there is nowhere else to point, and they are simply locked out of it. That is what #823 turned out to be — the adapter settings pair, missed because the tier rule was depth-1. The bias stays; the map has to be right about the adopter's tier at every depth for the bias to be safe.

A **third** question builds on the first: `is_synced_copy(target_root, path)` — *does this path arrive here as a copy a sync makes from the methodology's source?* Documentation places ask it: a synced copy is never a place, so that a sync never shows up as friction in the project's own history ([living-docs:DEC-001-living-docs-discipline] point 1). Its consumers are the friction pass, which loads this module from the tree and tests every match of every declared place with it (`synced-place`, the schemas README, "The friction block"), and the packages pass of `pkit validate`, which asks it of a package file to name the fix that lasts (the journal warning in "Validation: the package schema"). It is `is_sync_managed` **and** the repository not being the methodology's own source (`is_methodology_source`). The source repository is the one whose `.pkit/` is the methodology's own tree. The tool recognises it by sync's self-host test, which the ownership module cannot import, so the predicate recognises it by the marker in "The methodology's literals" above — the package source beside the `.pkit/` tree, the same test the entry-point router runs (the dispatcher is not a marker). The router's first route is what keeps the predicate's answer equal to sync's, and tests hold the predicate both to the router's markers and to sync's own decision ([ADR-059](../../tech-docs/architecture/decisions/ADR-059-methodology-source-repository.md)). The difference from `is_sync_managed` is deliberate. In the source repository the kit's trees stay the kit's to manage — write authority does not move — yet none of them is a copy, because the tree is what a sync would copy from; its self-host sync re-runs the deploy primitives and propagates nothing ([ADR-055](../../tech-docs/architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3). In an adopter, the backbone's trees and a `kit-shipped` capability's are copies; an `incubated-in-repo` capability, an unregistered one and every `project/` tier are not. The verdict keys on origin and on the repository, never on the path, so the same `.pkit/` README is a place in the source and refused in an adopter.

## Worked example

A full worked example demonstrating the upgrade flow across backbone + components is deferred for a focused rewrite. The prior example was built around the now-retired bundle pattern (per [COR-027](../decisions/core/COR-027-alternative-impls-as-capability-data.md)); rewriting it against the capability + adapter shape is queued.

For concrete examples of the contract this document defines, see:

- The kit's own `.pkit/manifest.yaml` for the backbone-manifest shape with adapter and capability entries.
- `.pkit/migrations/backbone/<X.Y.0>/` for backbone migration script structure.
- `.pkit/capabilities/project-management/migrations/0.12.0/` for a capability-tier migration that handles file-rename + adopter-state cleanup.
- `.pkit/adapters/claude-code/migrations/` for adapter-tier migration patterns.
