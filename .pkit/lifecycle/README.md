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

The table lists every key `.pkit/schemas/backbone/package.schema.json` knows, with its shape and the record that owns it. **The schema is the authority**: where the table and the schema disagree, the table is the defect. A key the schema does not know is a warning, not an error, until the strict flip (see "Validation" below).

**Required.** The schema requires `component` and, inside it, `kind`, `name` and `version`; every other top-level key is optional. COR-017 also lists `schema_version`, `description` and `requires_backbone` among a capability's required fields, and every shipped capability carries them; the schema, which serves adapters too (the adapter has no `description`), does not enforce that.

| Key | Shape and meaning | Owning record |
|---|---|---|
| `schema_version` | The package file's own version: the integer `1` or `2`, both accepted, and a file without the key reads as `1`. See "Validation" below for what each marks. | COR-017; COR-021 (the `2`) |
| `component` | `kind` — `capability` or `adapter`; `name` — a component name (lowercase letters, digits and hyphens, starting with a letter and not ending with a hyphen) equal to the component's directory; `version` — the component's own semver, which gates dependency edges. | COR-010, COR-017 |
| `description` | A non-empty line: the summary `pkit capabilities list` shows, which the dispatcher also uses as the command group's help. | COR-017; COR-021 |
| `requires_backbone` | A version range of compatible backbone versions; must parse. Evaluated at install and upgrade, and checked by `pkit validate` against the installed backbone ("How the wiring is resolved", below). | COR-010, COR-017 |
| `requires_capabilities` | A list of `{name, version}`, both required: a component name and a version range, which must parse. Gated at install, upgrade and uninstall, and checked by `pkit validate` against the installed versions; absence means no dependencies. | COR-030 |
| `commands` | The command tree registered under `pkit <capability>`. A key is a token. A value carrying `script` is a leaf and also needs `help` (one line); `script` is a path relative to the component root and must exist. A leaf may declare `query-contract: true` — the one constant declaration that the command is a query (bounded, deterministic, read-only, needing no network; ADR-057 point 3), required on the command a validator names. Any other value is a group of further tokens. | COR-021; ADR-057 and ADR-058 (the declaration) |
| `aliases` | A list of unique component names: other namespaces for the same command tree (`pm` for `project-management`). | none — the dispatcher's, beside COR-021 |
| `validators` | A mapping from a validator name (a word) to its entry: `command`, required — a command reference (below) naming a leaf of this component's `commands:` tree, which must exist and declare `query-contract: true`; the leaf's `help` is the validator's — plus optional `order` (an integer; the backbone's members take the orders below 1000, and 1000 is the default). `pkit validate` runs each as a member addressed `<component>:<name>`: the leaf's script from the project root with the one argument `--json`, the offline marker set ("The methodology's literals" below), under the query policy of the one command runner ("How a registered command is run" below) — in its own process group, bounded by the backbone's thirty seconds and killed as a group when it overruns — answering on stdout with one JSON document and nothing else — `{"summary": [...], "findings": [{"severity", "location", "message"}]}`, severity one of `error`, `warning`, `info`, `report`, a finding optionally carrying a `label`; diagnostics go to stderr; only `error` fails. No answer — a leaf without the declaration, an abnormal exit, a timeout, not exactly that document — is an error finding. No shipped component registers one yet. | ADR-058 |
| `provides` | A mapping from hook name to an implementation string. Reserved; no shipped file uses it. | COR-013 |
| `footprint` | A list of unique relative paths or globs: what the component deploys outside `.pkit/`, aggregated across components and routed into `.git/info/exclude` by `pkit visibility private`. | ADR-009 rule 1 |
| `runtime_ignore` | A list of unique relative paths or globs: runtime-local files to git-ignore, aggregated into the pkit-owned `.pkit/.gitignore`. A component names only paths it owns; the backbone declares its own through a core-level seam. | ADR-009 rule 7 |
| `connections.roles` | A list of unique qualified role names, `<publisher>::<role>`: the roles this component provides. Every point it defines sits under one of them. | COR-053 points 1 and 3 |
| `connections.extension-points.accepts` | A mapping from point address, `<publisher>::<role>:<point>`, to a data point this component defines: `schema_version`, `schema` (its companion JSON Schema, relative to the component's `schemas/`; must exist) and `description`, all required, plus optional `combination` (`single` or `union`) and `mandatory`. | COR-053 point 2; COR-052 points 1, 3 and 5 |
| `connections.extension-points.offers` | A mapping from point address to a process or event this component offers: `kind` (`process` or `event`), `schema_version` and `description`, all required. `kind: process` also requires `process`, the offered definition's id; `kind: event` also requires `command` (the emitting command), `schema` (the payload's companion under `schemas/`; must exist) and `subject` (the payload field naming the subject). | COR-053 point 2; COR-036 |
| `connections.extensions.contributes` | A list of contributions to another role's data point: `point` (an address) and `schema_version`, required, plus optional `command` (a command filler), `description` and `mandatory`. | COR-053 point 3; COR-052 point 6 |
| `connections.extensions.subscribes` | A list of subscriptions to another role's event: `point`, `schema_version` and `command` (the subscriber), all required, plus optional `description` and `mandatory`. | COR-053 points 2, 3 and 9 |
| `connections.extensions.depends-on` | **Generated, never hand-written**: `generated: true`, required, and `entries`, a list of `{process}` plus optional `schema_version` and `mandatory`; `process` is in the implementation form `<capability>:<process-id>` or the role form `<publisher>::<role>:<point>`. | COR-053 point 4; COR-038 |
| `mandatory` — on a data point, a contribution, a subscription or a `depends-on` entry | `{reason}`, a non-empty reason required: the mark without one is refused. An offered point takes no mark. | COR-053 point 6 |
| `docs.locations` | A mapping from a location name (`[a-z][a-z0-9-]*`) to `{path}` plus optional `root` (`internal`, the default, or `user`) and `description`; `path` is a sub-path of that documentation root. | COR-049 point 4 |
| `friction.places` | A list of `{path}` plus optional `location` (a name declared in `docs.locations`, inside which `path` applies; without one, `path` is repository-relative) and `description`. | COR-050 point 1 |
| `friction.surface` | A list of unique repository-relative paths or globs this component says ought to be described; the part no artefact anchors to is reported as uncovered. | COR-050 point 8 |

What holds across the table:

- **Two kinds of `schema_version`.** At the top level it versions the package file. Everywhere else — a data point, an offered point, a contribution, a subscription, a `depends-on` entry — it is the *point's* version, an integer from 1, and two versions are compatible when they are equal (COR-053 point 5).
- **Command references** — `command` on an offered event, a contribution, a subscription or a validator entry — are a path through the `commands:` tree, tokens separated by single spaces (`create page`), landing on a leaf that exists.
- **Paths** — every `script`, `schema`, `docs.locations` path, `friction` place and surface entry, `footprint` and `runtime_ignore` entry — are relative, with no `..` segment; the repository check names the offending segment.
- **Write role names and addresses in words.** The schema types them loosely — each part any run of characters other than whitespace and `:` — but the configuration file's selection keys admit only *words*, `[a-z][a-z0-9-]*`, and so does the filler mapping below. A role or point whose parts are not words cannot be selected in the configuration file and has no filler path.
- **Ahead of the schema.** COR-052 point 3 decides a third combination policy, `additive`, which the schema does not admit yet, so `combination: additive` is refused today; and COR-052 point 1 asks a data point to declare how the definer's default takes part and its inert policy, keys the schema does not know yet, so they would warn as unknown. They arrive with the data-point resolution, #994.

**Casing.** Two spellings meet in this file, and both stay.

- The keys that predate the connection-points record are snake_case — `schema_version`, `requires_backbone`, `requires_capabilities`, `runtime_ignore` — like the backbone's other YAML (the manifests above; the schemas README, "YAML conventions").
- The compound keys COR-053 decides by name are kebab-case — `extension-points`, `depends-on` — written as the record spells them, because a record that names the keys people write decides their spelling (COR-053 point 3 and its Rationale; COR-050 point 1 says the same of the friction block).
- Every other key inside `connections`, `docs` and `friction` is a single word. `schema_version` keeps its snake_case there because it is the field that carries a point's version everywhere that version is written — a filler envelope, a role block's point block (COR-052 point 5, COR-053 point 10).
- One near-collision to mind: the generated `depends-on` here is copied from the process definitions' `depends_on` (COR-038) — one fact in two files, each spelt as its own record spells it.

No record decides a casing rule for the whole file, and renaming either family would be a surface change owing a migration (COR-010) for no reader's benefit. **A new key** is spelt as the record that decides it spells it. Where no record names it, it is a single word if one suffices; a compound is kebab-case inside `connections`, `docs` and `friction`, and snake_case at the top level, like the keys it sits beside.

#### Validation: the package schema

Every `package.yaml` validates against one backbone file schema, `.pkit/schemas/backbone/package.schema.json` (Draft 2020-12; the class is described in the schemas README's "Backbone file schemas" section and placed by ADR-056). It is read from the tree of the project being validated, never from a copy in the binary, so a tree recorded before it landed skips the shape checks and reports so. The validator is `project_kit.package_validate`; two callers run it on the same code: `pkit validate` (the **`packages`** member, over every capability and adapter the backbone manifest registers — ADR-058) and the register pre-flight below (for the one incubated capability about to be activated).

- **Two `schema_version` values are in use, and both are accepted.** Version 1 is the scaffolded default (`claude-code`, `living-docs`, `software-analysis`, `software-engineering`); version 2 marks the files that adopted the `commands:` block when COR-021 said the version bumps with it (`demo-recording`, `evidence`, `project-management`). No reader distinguishes the two — the dispatcher reads `commands:` from either — and every field is optional in both, so the schema accepts `1` and `2` as an integer enum and nothing is bumped or migrated. A third value is an error until a record introduces it.
- **Known keys are strictly typed; unknown keys warn.** The schema leaves `additionalProperties` open at the top level and inside the blocks below, so an unknown key is not a schema error: the validator reports it as a **warning** with the nearest known key suggested (`unknown key 'foootprint'; did you mean 'footprint'?`), through the one renderer every backbone file schema shares (ADR-056 point 4). Warnings never fail `pkit validate` or refuse a register. **Flipping to strict — unknown keys as errors — is Task #999**, taken once every block is known; the schema's description says so.
- **Repository checks**, all errors: `component.name` equals the directory name; `component.version`, `requires_backbone` and every dependency range parse; every command `script` exists; a declared connection point sits under a role in `connections.roles`; an accepted data point's (and an offered event's) companion `schema` exists under the capability's `schemas/`; every command a point or extension names exists in `commands:`, and every command a validator names exists there and declares the query contract; `docs.locations` paths, `friction` places and surface entries, `footprint` and `runtime_ignore` entries are relative sub-paths (no absolute path, no `..`), and every command `script` path is relative; a place's `location` is a declared one. The checks *across* packages — roles, points, mandatory marks, cycles, fingerprints and the version relations — are the wiring resolver's ("How the wiring is resolved" below), run by `pkit validate` as its `connections` and `versions` members; `package_validate.check_wiring` is the same resolution for the pre-flight, and `resolve_active_roles` answers which roles have an active provider.

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
        combination: union                         # optional: single | union
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
      - { point: pkit::analysis:glossary, schema_version: 1, command: export-glossary }
    subscribes:                                    # events it reacts to, with its command
      - { point: pkit::analysis:use-case-created, schema_version: 1, command: refresh }
    depends-on:                                    # GENERATED from process definitions' depends_on (COR-053 point 4)
      generated: true                              # the mark; a hand-written copy without it is refused
      entries:
        - { process: project-management:issue-lifecycle }

# COR-049 point 4 — the sub-paths of this component's own documents, relative to a documentation root.
docs:
  locations:
    pages: { path: pages, root: user }             # root: internal (default) | user; relative sub-paths only
    spaces: { path: spaces }

# COR-050 points 1 and 8 — where anchored artefacts live, and the surface that ought to be described.
friction:
  places:
    - { location: pages, path: "**/*.md" }         # inside a declared location…
    - { path: "notes/**/*.md" }                    # …or, without one, inside the project
  surface: ["src/**"]                              # repository-relative globs
```

`depends-on` is the one block a person never writes: the refresh command regenerates it from the process definitions and marks it `generated: true`. Validation fixes the shape and the mark, and the wiring resolver reads the entries; a stale copy is the refresh command's check (Task #995), since detecting it means reading the process definitions the resolver never opens.

#### The methodology's literals

Three names the core records need are written record-neutrally, and the literal is left to the distribution's reference ([COR-053](../decisions/core/COR-053-connection-points.md), the vocabulary paragraph of its Decision). This is that reference. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The publisher qualifier the methodology reserves for the roles it defines, written `<methodology>::` (COR-053 point 1) | **`pkit::`** | Role names (`pkit::documentation`) and point addresses (`pkit::documentation:readers`): in the `connections` block above, in the configuration file's `connections.providers` and `connections.selections` keys, and as a role block's key where the qualified form is needed. |
| The one front-matter key "owned by the methodology, named for it" (COR-053 point 10) | **`pkit:`** | An artefact's front matter, or a collection entry: the container (the schemas README, "The container"; `backbone/container.schema.json`). |
| "a sub-path the backbone owns for slot files", under the internal documentation root ([COR-052](../decisions/core/COR-052-slots.md) point 2) | **`pkit/fillers/`** | The prefix of every project filler file (the next section). |

**The qualifier names who defined a role, never who implements it** (COR-053 point 1). A third party coins its roles under its own name — `super-docs::documentation` is a different role that shares a word with `pkit::documentation` — and may also *provide* a `pkit::` role, interchangeably with the capability that first defined it, but it never coins a role under `pkit::`. Project-published roles have no qualifier yet; COR-053 leaves them to a later refinement. **The container key is not a qualifier**: an artefact has one `pkit:` key whoever published its roles, and a third party's role block sits inside it, beside the methodology's own blocks (COR-053 point 10).

These strings are this distribution's choice, not a principle: another distribution of the same records could choose others. Changing one would change files adopters have written, so it would be a surface change shipping a migration (COR-010), not a record amendment.

**Two more literals, for query commands.** [ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 3 leaves the literal of the query-contract declaration and the offline marker to this reference, specified with the first query commands that run — the validators [ADR-058](../../tech-docs/architecture/decisions/ADR-058-validator-registry.md) registers. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The one constant declaration that a command honours the query contract — bounded, deterministic, read-only, needing no network (ADR-057 point 3) | **`query-contract: true`** | On a `commands:` leaf, beside `script` and `help`. Required on the command a validator names: the `packages` member reports one without it, and the validator runner refuses it. |
| The offline marker, "so a well-behaved command can tell" (ADR-057 point 3) | **`PKIT_OFFLINE=1`**, with **`UV_OFFLINE=1`** beside it | The environment of every query command `pkit validate` starts. `PKIT_OFFLINE` is what a command reads; `UV_OFFLINE` is honoured by `uv`, so a script with a `uv run --script` shebang resolves its dependencies from uv's cache and never fetches. |

**How dependencies are provisioned before an offline run.** The umbrella never fetches, so a script's dependencies must already be in uv's cache when it runs. Running the leaf once as its focused surface (`pkit <capability> <command>`) provisions them — the dispatcher sets no marker — and a pipeline does the same before its gate. A dependency that is not cached makes the command fail to start, which the umbrella reports as no answer: an error finding.

#### How a registered command is run

The backbone runs the commands a component registers through one runner, `project_kit.command_runner` — one lookup and one bounded run, with a policy per kind of command ([ADR-057](../../tech-docs/architecture/decisions/ADR-057-backbone-engines-and-command-limits.md) point 5; the kinds share one command runner, [COR-053](../decisions/core/COR-053-connection-points.md) point 11).

- **The lookup.** A command is a leaf of the `commands:` tree ("Field layout and casing" above), and one walk reads the tree: a command reference — a path of tokens — names a leaf through it. The dispatcher (`pkit <capability> <command>`), package validation, the validator registry and the process engine's predicate runner all read the tree this way, so each resolves a leaf to the same script. A process predicate's `run:` names a leaf by its own name rather than its path (the process README, "The predicate runner").
- **The run.** The leaf's script is started with an explicit argument list — never a shell string — from the project root, in its own process group, with standard output and standard error captured: standard output is the answer, one JSON document and nothing else; standard error is diagnostics. The run is **bounded by thirty seconds**, a fixed backbone constant (`COMMAND_TIMEOUT_SECONDS`), not a setting (ADR-057 point 3). Exceeding it **kills the whole process group** — a script with a `uv run --script` shebang starts its interpreter as a grandchild, which killing the script alone would leave running — and an interrupt of `pkit` itself kills the group too. A run that does not start, exits non-zero, overruns, or prints anything but one JSON document is never an answer; what it is instead is the policy's.
- **The policies.**

  | Policy | Run by | Arguments and environment | The answer | No answer is |
  |---|---|---|---|---|
  | predicate | the process engine, for every predicate a process definition declares | the subject and `--json`; the environment unchanged — a predicate may reach the network | a JSON object the engine interprets (the process README, "The predicate runner") | indeterminate, fail-closed: a gate stays shut |
  | query | `pkit validate`, for a component's validator (ADR-058) | `--json`; the offline marker set ("The methodology's literals" above); the leaf must declare `query-contract: true`, or it is not started | the findings document (the `validators` row above) | an error finding |

  A subscriber's policy arrives with the events that run subscribers ([COR-053](../decisions/core/COR-053-connection-points.md) point 9 sets its limits).

The dispatcher's proxy is not a run in this sense: `pkit <capability> <command>` is a person's focused surface, so it takes the lookup, inherits the terminal's streams, and is neither bounded nor captured.

#### Where a project filler file lives: the address-to-path mapping

A project answers a data point with a file of its own (COR-052 point 2). The file's location is **derived from the point's address, never declared**, and the location rule binds the file to the backbone's filler schema by that path ([ADR-056](../../tech-docs/architecture/decisions/ADR-056-backbone-file-schemas-home.md) point 2). The mapping must be **path-safe**, because an address contains `::` and `:` (COR-053 Implications), and **injective on valid addresses**, so that no two points share a file and no path binds the wrong schema (ADR-056 point 2). This section defines it and its inverse.

**Valid addresses.** A *word* matches `[a-z][a-z0-9-]*`: a lowercase letter, then lowercase letters, digits and hyphens. A valid address is `<publisher>::<role>:<point>` with each part a word — the grammar `config.schema.json` applies to the keys of `connections.providers` and `connections.selections`. Because `:` is not a word character, a valid address splits into its three parts in exactly one way. The package schema types addresses more loosely ("Field layout and casing"); an address outside the grammar has no filler path.

**The mapping.** One directory per address part, the point as the file name:

```
<publisher>::<role>:<point>   ↦   <internal-root>/pkit/fillers/<publisher>/<role>/<point>.yaml
```

`<internal-root>` is the internal documentation root: `docs.internal` in the configuration file, default `docs/`. The prefix `<internal-root>/pkit/fillers/` is a documentation location derived like any other, so COR-049's rules apply to it. It is recorded when first used, and a root changed later moves no filler already placed ([COR-049](../decisions/core/COR-049-documentation-roots.md) points 4 to 6). Recording it belongs to the location rule, which arrives with #994 (below). The mapping fixes only what follows the prefix. `pkit/fillers/` is the backbone's sub-path, the third literal above. Its `pkit/` segment marks the folder as the methodology's among the project's own documents, as the `pkit:` key does in front matter. Because the backbone owns the sub-path, no component places documents in it (COR-052 point 2).

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

**What the file holds — arrives with #994.** The envelope is the backbone's (COR-052 point 2). Its schema under `backbone/`, the location rule that binds a file to it by this path, and the resolution of the entries all land with the data-point Task, #994, and that schema is then the authority. The shape it implements:

```yaml
schema_version: 1       # the version of the point this file targets (COR-052 point 5)
entries:                # the point's entries, in the point's own shape (its companion schema)
  - id: operator
    # …the fields the point's schema defines
suppress:               # optional, union points: entries from other fillers to drop, each with its reason
  - { id: guest, reason: "No anonymous readers on this project." }
remove:                 # optional, additive points: removal overrides, each with its reason
  - { id: security-review, reason: "Covered by the platform team's own gate." }
```

What the records already fix around it:

- **Precedence.** In `single` and `union` points the project file beats a capability, which beats the definer's default (COR-052 point 4).
- **Overrides.** In a `union` point, a project entry whose id matches a capability's entry replaces it whole, never field by field (COR-052 points 3 and 4). In an `additive` point the same collision is an error, and only `remove` takes an entry out (point 3).
- **Errors the project can fix.** A malformed envelope, or one targeting the wrong version of the point, is a validation error whatever the point's inert policy (COR-052 point 2).
- **Inert, not wrong.** A filler whose point has no active provider has its envelope checked and its body left alone, and is reported as inert (ADR-056 point 2).
- **Editor support.** The authoring command that creates a filler file stamps the editor directive at the backbone schema's path (ADR-056 point 1).

#### How the wiring is resolved

`project_kit.connections` is the **single wiring resolver** (COR-053 point 7): `pkit validate` reports it, and the graph, the status report and the install / uninstall plans (points 7 and 8) read its `Wiring` rather than computing wiring of their own — a plan resolves the installed set plus or minus a candidate through the same function. It reads only package metadata (with the companion schemas its points name), the configuration's `connections` block and the installed versions; it runs no filler command and parses no process definition. It is deterministic: the same repository state yields the same wiring and the same findings, in the same order.

- **Provider selection.** One installed capability providing a qualified role is its active provider. Two or more need the `connections.providers` entry naming one; without it the role is in *conflict* — an error located at that key, with the entry to add and the `pkit config set` command that adds it — and no provider's points are defined. An installed provider that is not the selected one keeps its commands, but its points are not defined and its own extensions are inert; it is warned. A selection naming a capability that does not provide the role is the configuration pass's error (below).
- **Compatibility is an equal integer.** A contribution, subscription or `depends-on` entry binds to the active provider's point when its `schema_version` equals the point's; otherwise the counterpart is **inert**, warned, and delivered nothing. A counterpart naming a point its role's active provider does not define is warned with the points it does define. A `depends-on` entry may omit the version and binds on existence alone — an offered process point in the role form, or, in the implementation form `<capability>:<process-id>`, an offered point with that `process` id or a definition file at `schemas/<process-id>.yaml` (existence only; a definition kept under another file name is not found this way).
- **Optional by default; mandatory with a reason.** A counterpart to a role nobody provides, or to an upstream whose capability is not installed, is silent unless marked mandatory. A mark on an accepted point is unmet when nothing but the default fills it; on a contribution or subscription, when no compatible target exists; on a `depends-on` entry, when the upstream is missing or at another version. An unmet mark is an error on the side carrying it, with the fix named (meet it, or drop the mark); the capability it targets, when there is one, is warned with the carrier named — COR-030's direction split, as COR-053 point 6 applies it. Unmet marks are reported with the connections, whatever their cause.
- **Cycles.** Mandatory marks that face each other — every strongly connected group of capabilities joined by mandatory connections — are rejected, an error on each mark in the cycle: no member could be installed first. An edge is drawn only to a role's *active* provider, since which provider is selected decides whether a cycle exists; an unselected provider's marks bind nothing.
- **Fingerprints.** Two installed providers of one qualified point and version must define the same companion schema. The fingerprint is the sha256 of the schema's canonical JSON — key order and layout never count, any other difference does — compared and kept nowhere; a disagreement is an error on each provider.
- **The contributor selection.** A `single` data point with contributions from more than one capability needs the `connections.selections` entry naming one; without it, an error at that key.

**Version relations.** Each relation is checked deterministically and reported by functionality: the resolver's under a `versions` heading, which counts how many of each were checked and labels each finding with its relation.

| Relation | Checked | Finding |
|---|---|---|
| Backbone range | each component's `requires_backbone` admits the installed backbone version | error on the component — `[backbone range]` |
| Capability dependency ranges | each `requires_capabilities` entry names an installed capability whose version of record (its component manifest, else its package) the range admits — the order the install gate reads | error on the dependent, warning on the dependency naming each dependent — `[capability dependency range]` (COR-030) |
| Contributions and subscriptions against point versions | the counterpart's `schema_version` equals the point's | warning: the counterpart is inert — `[point version]` |
| Process connections against interface versions | a `depends-on` entry's `schema_version`, where it declares one, equals the offered process point's | warning: the entry is inert — `[process interface version]` |
| Project filler files against schema versions | the filler envelope's `schema_version` equals the point's | error at the filler — `[project filler version]`. The file sits at the path "Where a project filler file lives" gives; the hook `project_filler` answers nothing until the envelope's schema and the location rule ship (Task #994), and the comparison is in place |
| Rule-set inheritance pins | each `inherits` pin of a rule-set file against the major of the set it names (COR-051 point 7); the pins are read from the rule-set files by `rule_sets.pin_checks` (the schemas README, "Rule-set files") | error on the inheriting rule set, naming the new major — `[rule-set pin]`. A pin naming no set, or one it may not inherit, is the `rule-sets` pass's finding |
| Configuration shape against the installed backbone | the configuration file carries no version key; the configuration pass validates it against the `config.schema.json` the installed backbone ships in the tree (ADR-056 point 1) | reported under `configuration` |

A mandatory counterpart at another version is reported with the connections, as an unmet mark (above). The configuration pass checks the two selection keys against the same declarations (`connections.load_declarations`): a provider entry names a capability that provides the role; a contributor entry names a `single` data point some installed provider defines and a capability that contributes to it.

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

- **Self-consistency validation (COR-031 D1)** — the adopter hand-authored this capability; nothing upstream validated it. Before activation, its own `package.yaml` (run through the same package validator `pkit validate` uses — the schema and the repository checks in "Validation" above; only its errors refuse, its unknown-key warnings do not), required layout (`README.md`), and own schema pairs (validated by the same validator `pkit schemas validate` runs) are checked against the working tree, which is its spec. Refuse with the structural problems listed. This is *self-validation*, not source-reconciliation — origin suppresses the latter (below), never the former.

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

### The downgrade guard on capability refresh (issue #524)

The `kit-shipped` refresh above copies the source subtree wholesale. On its own that is direction-blind: a source *older* than the installed version would overwrite newer committed state with stale content — the exact data loss reported in #524, where a mis-pinned source refreshed an installed capability back several minor versions. So before refreshing a `kit-shipped` capability, `sync` compares the **source** version to the **installed version of record** (the per-component `manifest.yaml`, falling back to the installed `package.yaml` — what the refresh would actually overwrite):

- **source version < installed version (a downgrade):** refuse this capability's refresh, print a `refused` line naming both versions, and leave the installed tree untouched. `sync --force` overrides — the downgrade proceeds, but a loud `downgrade` line records the deliberate overwrite. Under `--dry-run` the refusal is *previewed* (not a "would refresh") so the plan is honest.
- **source version ≥ installed version:** refresh as before.

The guard is defence in depth, orthogonal to *why* the source is stale, and fires only on an unambiguous downgrade — an absent or unparseable version on either side is treated as "not a downgrade" so an unreadable manifest never blocks a routine sync. It is scoped to the `kit-shipped` refresh branch: the incubated skip-branch above is unchanged (no kit source to compare against), and the "no longer ships from source" orphan case is likewise untouched.

### The ownership predicates (`ownership.py`)

The tier map above — which trees the kit owns, which are the project's, and how a capability's `origin` changes the answer — is also a question *other* layers need to ask. `.pkit/lifecycle/ownership.py` answers it as `is_sync_managed(target_root, path)`, and every consumer imports that one definition.

It answers a **second, narrower** question beside it: `is_adopter_owned_by_tier(rel_posix)` — *does this `.pkit/`-relative path sit on the project side of the no-shared-files split, by tier alone?* The two are not interchangeable, and picking the wrong one is a real error. `is_sync_managed` additionally consults a capability's **registration** (an unregistered or `incubated-in-repo` capability is not sync-managed whatever its tier) and reads everything *outside* `.pkit/` as unmanaged — so `src/`, which legitimately ships, answers False. A caller asking "may this be distributed?" needs the tier predicate; a caller asking "is this the kit's to manage, so an agent may not claim write authority over it?" needs `is_sync_managed`. Note what that second question is **not**: `pkit sync` does not call it. Sync decides what it writes through the copy path's own ownership handling, so a wrong answer here cannot overwrite an adopter's file — it can only misplace write authority. The name invites the other reading, and #823 was filed on exactly that misreading. Pass **`is_adopter_owned_by_tier`** a file path: its depth-free `project/` case reads every part except the last, so a directory path naming the tier itself (`agents/project`) answers False — though its other cases do match on a final component, so this is a rule about that case rather than about the whole predicate. `is_sync_managed` is deliberately the other way: it matches the declared tier positions by *prefix*, so the tier directory itself answers "the adopter's" — its consumer passes overlay entries, which are usually directories. "Is this *directory* the adopter's tier?" is a different question, and the packaging hook declares its own answer rather than asking this predicate.

It lives here rather than in the CLI package for the reason [ADR-003](../../tech-docs/architecture/decisions/ADR-003-permission-core-code-home.md) records for the permission decision core: an adapter's deploy primitive runs **in the adopter's tree**, where the globally-installed `pkit` runtime is not importable. Propagated in-tree code is the only home both the CLI and a propagated adapter script can reach, so the area is propagated and the module ships with it. Dependency direction is inward — the CLI imports it, each adapter imports it, and it imports neither.

`is_sync_managed`'s first consumer is the agent-overlay write-authority check ([ADR-051](../../tech-docs/architecture/decisions/ADR-051-process-author-edit-authority.md)): a *write-carrying* overlay category may not name sync-managed content, which is the no-shared-files invariant applied at the agent surface. The module also declares that category set (`WRITE_CARRYING_CATEGORIES`), beside the predicate that guards it. Re-deriving either per adapter would fork the ownership rule and silently skip the check on the next harness, so a test fails any adapter script that carries a copy.

`is_adopter_owned_by_tier`'s consumers are the packaging build hook (`hatch_build.py`) and the test that holds it honest — plus one expression of the rule that deliberately does not call it: the sdist's `withhold` globs, a build-hook option in `pyproject.toml` that mirrors the same cases by hand. The hook could apply the predicate to the sdist as well; it does not, so that the sdist's filter stays independent of the wheel's and the test comparing the two artifacts can catch a hole in the predicate. That copy is the one to check first when the two distributions disagree. The wheel bundles the methodology tree by force-include, and hatchling's `exclude` cannot filter force-included paths — so the manifest carried its own idea of which paths were adopter-owned, **disagreed with this module, and nothing could notice**: 51 adopter-owned files shipped, including git-ignored runtime state that made the artifact depend on the build machine. Deriving the boundary from this predicate is what closes that, and it is the same lesson ADR-051 records one altitude down — a second copy of an ownership rule forks silently.

`is_sync_managed` is deliberately **conservative under `.pkit/`**: anything the map does not recognise as project-owned reads as sync-managed. A false "not managed" would hand out write authority over kit content, which is the costlier direction and why the bias points this way. But the cost of a false "managed" was understated here as "a rejected overlay entry the adopter re-points": when the misjudged path is the adopter's *own* file, there is nowhere else to point, and they are simply locked out of it. That is what #823 turned out to be — the adapter settings pair, missed because the tier rule was depth-1. The bias stays; the map has to be right about the adopter's tier at every depth for the bias to be safe.

## Worked example

A full worked example demonstrating the upgrade flow across backbone + components is deferred for a focused rewrite. The prior example was built around the now-retired bundle pattern (per [COR-027](../decisions/core/COR-027-alternative-impls-as-capability-data.md)); rewriting it against the capability + adapter shape is queued.

For concrete examples of the contract this document defines, see:

- The kit's own `.pkit/manifest.yaml` for the backbone-manifest shape with one capability + one adapter entry.
- `.pkit/migrations/backbone/<X.Y.0>/` for backbone migration script structure.
- `.pkit/capabilities/project-management/migrations/0.12.0/` for a capability-tier migration that handles file-rename + adopter-state cleanup.
- `.pkit/adapters/claude-code/migrations/` for adapter-tier migration patterns.
