---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/backbone/package.schema.json
        - .pkit/schemas/backbone/filler.schema.json
        - .pkit/schemas/backbone/config.schema.json
        - .pkit/schemas/backbone/container.schema.json
        - .pkit/lifecycle/ownership.py
        - .pkit/cli/pkit
        - src/project_kit/__init__.py
        - src/project_kit/manifest.py
        - src/project_kit/install.py
        - src/project_kit/upgrade.py
        - src/project_kit/sync.py
        - src/project_kit/release.py
        - src/project_kit/capabilities.py
        - src/project_kit/scaffolds.py
        - src/project_kit/package_validate.py
        - src/project_kit/backbone_schemas.py
        - src/project_kit/validators.py
        - src/project_kit/command_runner.py
        - src/project_kit/run_cache.py
        - src/project_kit/provisioning.py
        - src/project_kit/dispatcher.py
        - src/project_kit/process_dependencies.py
        - src/project_kit/process_journal.py
        - src/project_kit/visibility.py
        - src/project_kit/refs.py
        - src/project_kit/docs_roots.py
        - src/project_kit/friction_discovery.py
        - src/project_kit/friction_check.py
        - src/project_kit/friction_report.py
        - src/project_kit/rule_sets.py
        - src/project_kit/changesets.py
        - src/project_kit/connections.py
        - src/project_kit/data_points.py
        - src/project_kit/point_questions.py
        - src/project_kit/capability_plans.py
        - src/project_kit/status.py
        - src/project_kit/report_context.py
        - src/project_kit/agent_runs.py
        - src/project_kit/pull_request_landing.py
        - src/project_kit/router.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/resolve-source.py
      record: [COR-010, COR-013, COR-017, COR-019, COR-021, COR-030, COR-031, "COR-033#P7", COR-036, COR-038, COR-041, COR-049, COR-050, COR-051, COR-052, COR-053, "COR-054#2", COR-055, COR-056, COR-061, "COR-062#2", "COR-070#2", ADR-009, ADR-050, ADR-056, ADR-057, ADR-058, ADR-059, ADR-065, ADR-066, ADR-076]
---

# Manifest schema

What the backbone manifest, each component's manifest and package metadata hold, and how the backbone runs what a package declares ([COR-010](../decisions/core/COR-010-resource-lifecycle.md), [COR-053](../decisions/core/COR-053-connection-points.md)).

## Contents

<!-- pkit:contents -->
- [Backbone manifest (`<project>/.pkit/manifest.yaml`)](#backbone-manifest-projectpkitmanifestyaml)
- [Per-component manifest (one per installed component)](#per-component-manifest-one-per-installed-component)
- [Package metadata (`package.yaml`)](#package-metadata-packageyaml)
- [Worked example](#worked-example)
<!-- /pkit:contents -->

## Backbone manifest (`<project>/.pkit/manifest.yaml`)

The backbone manifest is small by design: no component data is duplicated here, since that lives in each component's manifest.

```yaml
schema_version: 1
backbone_version: 2.1.0
completed_version: 2.1.0

# Component registry — paths to per-component manifests.
components:
  - kind: capability
    name: project-management
    manifest: .pkit/capabilities/project-management/project/manifest.yaml
  - kind: capability
    name: homegrown
    origin: incubated-in-repo                         ← in-repo (incubated) capability (COR-031)
    manifest: .pkit/capabilities/homegrown/project/manifest.yaml
  - kind: adapter
    name: claude-code
    manifest: .pkit/adapters/claude-code/project/manifest.yaml
```

The backbone manifest carries:

- **`schema_version`:** the version of *this* manifest's own schema, independent of any component's. Bumping it triggers a backbone manifest-schema migration.
- **`backbone_version`:** the release whose content the project holds. While a transition is incomplete, it names the transition's target instead. A transition writes it first, before anything else ([`upgrade-flow.md`, "The upgrade flow"](upgrade-flow.md) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->).
- **`completed_version`:** the last release a transition of the backbone completed, written last. A project is at a version only when both keys name it. The key is optional:
  - **Missing:** the transition reads as incomplete with no lower bound. The project's backbone migration history is unknown, so its next upgrade runs every backbone migration once ([`upgrade-flow.md`, "The replay: a missing completion"](upgrade-flow.md#the-replay-a-missing-completion) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->). No manifest written before the release that added the key has it.
  - **Behind `backbone_version`:** an interrupted transition, which the next upgrade finishes.
  - **Ahead of `backbone_version`:** an older pkit's sync over a finished transition. It reads as incomplete too.
  - **How it is written:** each of the two keys is written by an edit of its own line, so neither write re-serialises the manifest. Both stay top-level scalars in every `schema_version`, and no manifest-schema migration moves them, so a pkit that reads only `backbone_version` still finds the target. The key needs no schema bump. The manifest's writer has kept a key it does not know since the first published release.
  - **Who writes it:** first install writes it last, and so does a transition of the backbone. In the methodology's own source repository, where no transition runs, its release step writes it beside `backbone_version`.
- **`components`:** the registry. Each entry is a `{kind, name, manifest}` triple pointing at a per-component manifest file, optionally carrying an **`origin`** marker (below). A capability's entry names `.pkit/capabilities/<name>/project/manifest.yaml`, whatever its origin. An entry an older release wrote may name the capability's root instead ("Where a capability's manifest lives", below).

### Capability origin (COR-031)

A capability-kind registry entry may carry an **`origin`** field recording where the capability came from. It is the property the lifecycle keys off to decide what `sync` and `upgrade` may do to the capability:

- **`kit-shipped`** (the default): the capability ships in the kit source and was copied into the adopter on `capabilities install`. This is the status quo COR-017 describes.
  - **The field is omitted when it holds this default.** An absent `origin` reads as `kit-shipped`, so every registration written before this field existed keeps its behaviour with no re-tagging. The change is purely additive, with no migration (COR-031 D2).
- **`incubated-in-repo`:** the capability was authored in the adopter's *own* repo and registered in place via `capabilities register`, with no copy. Its subtree is adopter-owned content, not a copy of anything the kit ships.

Origin lives **here, in lifecycle-owned install-state, never inside the capability's own subtree** (COR-031 D2). An incubated capability's subtree, its authored `package.yaml` included, is entirely adopter-owned. For an incubated capability, no kit-written per-component `manifest.yaml` is stamped at all. Its version of record is its authored `package.yaml`, and dependency gating reads from there.

## Per-component manifest (one per installed component)

A per-component manifest records one installed component: its kind, name, recorded version and install timestamp, its backbone range, and its opaque backend state.

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

Its sections:

- **`schema_version`:** the version of *this* component-manifest schema. Bumping it triggers a component manifest-schema migration.
- **`component`:** kind, name, recorded version, install timestamp.
- **`requires_backbone`:** a semver range pinned to this version of the component. It is recorded into the manifest at install and upgrade, so the next upgrade run can verify compatibility.
- **`backend_state`:** opaque backend identifiers the kit cannot rederive, such as board UUIDs and webhook IDs. It is empty, `{}`, for components that have none.
  - **`backend_state.skipped`:** in a capability's manifest, the skills and agents the project chose to skip on a naming collision (COR-017), each as a `{kind, name}` entry. A refresh reads them back from here, and leaves those artefacts out of its copy. A skip chosen in a transition is recorded here before the copy, so a transition a migration stops does not ask again. A name recorded here is never a new collision ([`upgrade-flow.md`, "A new collision"](upgrade-flow.md#a-new-collision) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->).
  - **A restamp** changes the version, the timestamp and the range. It replaces `skipped` with the skips in force, and keeps every other key of `backend_state`. It reads the manifest after the capability's migrations, so a key a migration wrote stays. A manifest that does not parse, such as one left with merge-conflict markers, is replaced by a new one, and the refresh says so.

**Notably absent:** enumerations of files, labels, symlinks, settings entries and templates. These are *derivable* state. The kit-side spec at the component's recorded version and the adopter's config tell you what should exist. The validate/upgrade reconciliation tells you whether reality matches.

### An adapter's manifest

An adapter's manifest sits at `.pkit/adapters/<name>/project/manifest.yaml`, and its registry entry names that path. The adapter's files move with the backbone, so its manifest only keys the window of its migrations.

- **Who writes it:** first install writes it for each adapter it copies, which it registers at the same time. A transition of the backbone writes it too:
  - an adapter with no manifest is recorded at the version the target ships, and runs none of its migrations
  - an adapter with a manifest is recorded at that version once the migrations in its window have run. Their scripts are read from the running pkit's bundle, since a project's copy of an adapter carries no `migrations/`. A manifest that records a newer version than the target ships refuses the transition before it writes anything. A transition never moves a recorded version down.
  - an adapter the target adds is registered after the copy, and recorded at the version it ships
- **What a project's copy holds:** each file at the adapter's top level, its declaration of the permission dimensions its harness enforces among them, and its core settings. A transition removes a top-level file the bundle no longer ships. The adapter's `project/` and `settings/project/` are the project's, and no copy touches them.
- **A registered adapter with no manifest** reads as at the backbone. Every project's adapter is in that state until its first transition under the release that writes the manifest.

### Where a capability's manifest lives

A capability's manifest sits at `.pkit/capabilities/<name>/project/manifest.yaml`. No copy of the capability's tree deletes or overwrites the manifest there, and the bundle ships none.

- **Who writes it:** a capability's install, and the restamp after a capability's migrations, in `pkit upgrade` and in `pkit capabilities upgrade`. Each of the two upgrades also records there, before its copy, each skip a person chose on a new collision. Each points the capability's registry entry at that path. Sync writes none.
  - An incubated capability is registered with the same path, and nothing writes a manifest there (COR-031 D2).
  - Nor does install in the methodology's source repository, so a capability's registry entry there names a path that holds no file.
- **A manifest at the capability's root,** `.pkit/capabilities/<name>/manifest.yaml`, is where older releases wrote it. There every copy deleted it or overwrote it. The code that writes the record moves it under `project/`:
  - `pkit upgrade` moves it right after recording its target, before its copy. `pkit capabilities upgrade` moves it after its checks, before its copy. A root manifest the restamp still finds came with the copy from the source, so the restamp removes it.
  - The move rewrites the registry entry's path, then removes the root file. So an interrupted move leaves two equal copies, and the next move finishes it.
  - The root manifest replaces one already under `project/`.
- **Which one is read:** every reader of a capability's recorded version, and of its skips, reads the root manifest where one exists. Otherwise it reads the one under `project/`, and where neither exists, it reads the capability's installed `package.yaml`.
  - The capability downgrade check, the dependency gates and the wiring resolver are among those readers.
  - `pkit validate`'s check of the manifests reads the one the registry entry names.
  - Both manifests exist only after an interrupted move, or after a write that does not know the move. Examples of such a write are an older pkit's restamp and a rollback of `.pkit/`. Either way the root one names the content the project holds, so it wins.
- **Read before propagation:** `pkit sync` and `pkit upgrade` read every capability's record before they copy anything, since a capability's copy replaces its installed `package.yaml`.
- **Sync moves none:** sync never copies a capability whose manifest is still at the root, since the copy would prune the manifest there. Such a capability, where the running pkit ships it at or above its recorded version, is reported pending `pkit upgrade`. The next `pkit upgrade` moves every root manifest, that of a capability it no longer ships included. `pkit capabilities upgrade` moves its own after its checks.

## Package metadata (`package.yaml`)

Every component, a capability or an adapter, ships a source-side `package.yaml`. The lifecycle reads this metadata at install and upgrade time, and the dispatcher reads it for commands. `pkit validate` checks it.

This section is the **package-metadata reference** the core records leave field layout and casing to (COR-053 point 3). It also records this distribution's literals and where a project's filler files live, which the records leave to the same reference.

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
# `optional: true` marks a dependency that need not be installed.
# Absence of this field (or an empty list) means no dependencies.
requires_capabilities:
  - name: project-management
    version: ">=0.20.0,<1.0.0"
  - name: living-docs
    version: ">=0.3.0,<1.0.0"
    optional: true

# Optional: this component's git-footprint paths outside `.pkit/`.
# `pkit visibility private` routes these into `.git/info/exclude`.
footprint:
  - .claude/skills

# Optional: this component's runtime-local files to git-ignore.
# Aggregated into the pkit-owned `.pkit/.gitignore`.
runtime_ignore:
  - .pkit/capabilities/<name>/project/some-runtime.log

# Optional, an adapter's alone: how its harness reaches each installed
# capability's loaded file. The backbone renders
# `.pkit/rules/capabilities.md` from it; the adapters README says how.
loaded_rules:
  entry: "@{file}"
  host: CLAUDE.md
  line: "@{index}"
```

### Field layout and casing

The table lists every key `.pkit/schemas/backbone/package.schema.json` knows, with its shape and the record that owns it. **The schema is the authority**: where the table and the schema disagree, the table is the defect. A key the schema does not know is an error, at any level ("Strict on unknown keys", below).

**Required.** The schema requires the fields COR-017 lists of every component, capability and adapter alike. They are `schema_version`, `component` with `kind`, `name` and `version` inside it, `description` and `requires_backbone`. Every other top-level key is optional.

| Key | Shape and meaning | Owning record |
|---|---|---|
| `schema_version` | Required: the package file's own version, the integer `1` or `2`, both accepted. See "Validation" below for what each marks. | COR-017 and COR-021 (the `2`) |
| `component` | `kind`: `capability` or `adapter`. `name`: a component name (lowercase letters, digits and hyphens, starting with a letter and not ending with a hyphen) equal to the component's directory. `version`: the component's own semver, which gates dependency edges. | COR-010, COR-017 |
| `description` | Required: a non-empty line, the summary `pkit capabilities list` shows, which the dispatcher also uses as the command group's help. | COR-017 and COR-021 |
| `requires_backbone` | Required: a version range of compatible backbone versions, which must parse. Evaluated at install and upgrade, and checked by `pkit validate` against the installed backbone ("How the wiring is resolved", below). | COR-010, COR-017 |
| `requires_capabilities` | A list of `{name, version}`, both required: a component name and a version range, which must parse. An entry may add `optional: true`. The dependency then need not be installed, but an installed one must satisfy its range. An optional entry never blocks uninstalling the capability it names. An entry without it is a required dependency. Gated at install, upgrade and uninstall, and checked by `pkit validate` against the installed versions. Absence means no dependencies. | COR-030 |
| `commands` | The command tree registered under `pkit <capability>`. A key is a token. A value carrying `script` is a leaf, and also needs `help`, one line. `script` is a path relative to the component root, and must exist. A leaf may declare `query-contract: true`, the one constant declaration that the command is a query (COR-050 point 2). A query is bounded, deterministic and read-only, and needs no network. The declaration is required on the command a validator names, on a command filler and on an anchor kind's resolver. A command filler's leaf may also declare `reads`, a non-empty list of distinct values among `history` and `settled`. `reads` says what the filler reads beyond the working tree. Without it, the filler reads the working tree only ("How a data point resolves"). `reads` on a leaf without `query-contract: true` is the `packages` member's error. Any other value is a group of further tokens. | COR-021. COR-052 point 6 (`reads`). |
| `aliases` | A list of unique component names: other namespaces for the same command tree (`pm` for `project-management`). The dispatcher binds them in one precedence walk. A backbone command wins, then a capability's own name, then the first capability in manifest order to declare the alias. An alias that loses reaches nothing. `pkit validate`'s `packages` member warns at the entry, naming what holds the name ("Validation: the package schema"). What holds it is the backbone command, or the capability whose name or earlier alias it is. It is a warning, since the alias is a shorthand: `pkit <capability> …` still reaches the capability. | none — the dispatcher's, beside COR-021 |
| `validators` | A mapping from a validator name, a word, to its entry. `command` is required: a command reference (below) naming a leaf of this component's `commands:` tree, which must exist and declare `query-contract: true`. The leaf's `help` is the validator's. `order` is optional: an integer, 1000 by default, and the backbone's members take the orders below 1000. `pkit validate` runs each validator as a member addressed `<component>:<name>`. It runs the leaf's script from the project root, with the one argument `--json` and the offline marker set ("The methodology's literals" below). It runs the script under the query policy of the one command runner ("How a registered command is run" below). The script runs in its own process group, bounded by the backbone's thirty seconds, and is killed as a group when it overruns. It answers on stdout with one JSON document and nothing else: `{"summary": [...], "findings": [{"severity", "location", "message"}]}`. `findings[].severity` is one of `error`, `warning`, `info` and `report`, and a finding may carry a `findings[].label`. Diagnostics go to stderr. Only `error` fails. No answer is an error finding: a leaf without the declaration, an abnormal exit, a timeout, or not exactly that document. | COR-055: a component joins validation by naming a command it registers (point 3), one severity fails (point 5), and no answer fails (point 6). |
| `provides` | A mapping from hook name to an implementation string. Reserved, and no shipped file uses it. | COR-013 |
| `footprint` | A list of unique relative paths or globs: what the component deploys outside `.pkit/`, aggregated across components and routed into `.git/info/exclude` by `pkit visibility private`. | — |
| `runtime_ignore` | A list of unique relative paths or globs: runtime-local files to git-ignore, aggregated into the pkit-owned `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content -->. The tier that writes a runtime file declares its pattern, whoever owns the directory it lands in. The backbone, which has no `package.yaml`, declares its own through a core-level seam. The process journals are among them: the backbone's engine writes them, and the backbone ignores them unless the project commits them. While they are committed, the render leaves out a component entry declaring them and names it in a comment line. The entry is warned too ("Validation: the package schema"). A component's entry lies in its own folder, `.pkit/capabilities/<name>/` or `.pkit/adapters/<name>/`. An entry outside it, or one with no `/` before its end, which matches at any depth under `.pkit/`, is the `packages` member's error. Every tracked file the render ignores is untracked, so such an entry would untrack another component's files. | ADR-009 rule 7; COR-033 P7 |
| `connections.roles` | A list of unique qualified role names, `<publisher>::<role>`: the roles this component provides. Every point it defines sits under one of them. | COR-053 points 1 and 3 |
| `connections.extension-points.accepts` | A mapping from point address, `<publisher>::<role>:<point>`, to a data point this component defines. `schema_version`, `schema` and `description` are all required. `schema` is its companion JSON Schema, relative to the component's `schemas/`, and must exist. `combination`, `default`, `inert`, `mandatory` and `question` are optional. `combination` is `single`, `union` or `additive`, and `single` when absent. `default` is `{value, participation}`, both required: the definer's own value, and `always` or `alone` (see "How a data point resolves"). `inert` is `fallback` or `fail`, and `fallback` when absent. `question` is a command reference naming the leaf of this component's `commands:` tree that asks the person about the point and records the answer. That leaf must not declare `query-contract: true`, since it writes ("A data point's question", below). | COR-053 point 2. COR-052 points 1 to 3, 5 and 6. COR-061 (`question`). |
| `connections.extension-points.offers` | A mapping from point address to a process or event this component offers. `kind` (`process` or `event`), `schema_version` and `description` are all required. `kind: process` also requires `process`, the offered definition's id. `kind: event` also requires `command`, `schema` and `subject`. `command` is the emitting command. `schema` is the payload's companion under `schemas/`, and must exist. `subject` is the payload field naming the subject. | COR-053 point 2 and COR-036 |
| `connections.extensions.contributes` | A list of contributions to another role's data point. `point`, an address, and `schema_version` are required. The data comes as `value`, written here, or as `command`, a command filler whose `commands:` leaf must declare `query-contract: true`. An entry holds one of the two, not both. `description` and `mandatory` are optional. | COR-053 point 3. COR-052 points 2 and 6. |
| `connections.extensions.subscribes` | A list of subscriptions to another role's event: `point`, `schema_version` and `command` (the subscriber), all required, plus optional `description` and `mandatory`. | COR-053 points 2, 3 and 9 |
| `connections.extensions.depends-on` | **Generated, never hand-written.** `generated: true`, required, and `entries`, a list of `{process}` plus optional `schema_version` and `mandatory`. `process` is in the implementation form `<capability>:<process-id>` or the role form `<publisher>::<role>:<point>`. `pkit capabilities refresh <name>` writes it from the process definitions' `depends_on`. It writes one entry per distinct upstream and targeted interface version, sorted. `schema_version` is the definition entry's `version`, and `mandatory` is its mark. A copy that differs is a validation error. | COR-053 point 4 and COR-038 |
| `mandatory` — on a data point, a contribution, a subscription or a `depends-on` entry | `{reason}`, a non-empty reason required: the mark without one is refused. An offered point takes no mark. | COR-053 point 6 |
| `docs.locations` | A mapping from a location name (`[a-z][a-z0-9-]*`) to `{path}` plus optional `root` (`internal`, the default, or `user`) and `description`. `path` is a sub-path of that documentation root. A location recorded for the name in `.pkit/capabilities/<name>/project/docs-locations.yaml` wins over the declared one. Every reader of a capability's locations, the documentation-roots readers and friction discovery, reads them this one way. An entry in another shape places nothing, and a place naming it is a validation finding. | COR-049 points 4 and 5 |
| `friction.places` | A list of `{path}` plus optional `location`, `type`, `revisits` and `description`. `location` is a name declared in `docs.locations`, inside which `path` applies. Without one, `path` is repository-relative. `type` is a name this component's `friction.types` declares: the type the artefacts in the place take. A `type` the registry does not declare gives no type, and the `packages` check reports it without failing. `revisits` is a non-empty list of links whose source's change asks for a revisit of their targets. Each link is `{targets, when}` or `{all-but, when}`, plus optional `description`. `targets` names the source's own field that lists the targets by their anchors' values. `all-but` names the own fields that list the anchors that stay out, every other anchor then being a target. It is a non-empty list of unique own fields. `when` names the trigger fields, a non-empty list of unique own fields. A link names exactly one of `targets` and `all-but`. A field is a word, never `pkit`. A link declares nothing when it names both or neither, or when its `targets` is not one own field. It declares nothing either when its `all-but` or `when` is not a non-empty list of own fields. The `packages` check refuses every link the schema refuses. What a link means: the schemas reference's page on backbone files, "A place may declare links". What the change check asks of a triggered link: the CLI reference, "Friction checks". `derived-links` is a non-empty list of forms of the links the component's command writes in the place's files. Each is `{target}` plus optional `description`. `target` is a regular expression an inline link's target matches whole, and the `packages` check fails one that does not compile. What friction does with them: the schemas reference's page on backbone files, "A place may declare derived links". | COR-050 points 1, 5 and 16. COR-056 point 2. |
| `friction.types` | The component's **type registry**: a mapping from a type's name to its entry. A name is a word of lower-case letters and digits joined by single hyphens, so it holds no `:` and no `/`. `description` is required. `kind-field` is optional: the artefact's own field in which an artefact of the type declares its kind, never `pkit`. Where the winning place gives such a type, an artefact takes it only when that field is present and not empty. `project-places` is optional, `false` by default: whether a project may give the type on its own places. The type's full name is `<component>:<name>`. How the backbone resolves an artefact's type from the places matching its file, and which findings it raises: the CLI reference, "Artefact types". | COR-056 points 2 to 4 |
| `friction.surface` | A list of unique repository-relative paths or globs this component says ought to be described. The part no artefact anchors to is reported as uncovered. | COR-050 point 8 |
| `friction.held` | A list of `{location, path}` plus optional `description`. `path` is a folder inside the declared location `location` names, or a glob of folders at one depth there, such as `*/revalidations`. A glob may stand only before the folder's own name: its last segment is plain, and it holds no `**`. A glob holds every file beneath each folder it names. Its files are the component's held documents, which no place reads as artefacts, its own component's places included. | COR-050 point 1 |
| `friction.kinds` | A mapping from an anchor kind to its entry. The kind is a word, as an anchor block and a rule's cited source write it. `command` is required: a command reference naming the leaf of this component's `commands:` tree that resolves an anchor of the kind. The leaf must exist and declare `query-contract: true`. The block is read for installed capabilities only. An adapter's entry registers nothing, and the packages check refuses it at the entry. How the backbone runs the resolver and reads its answer: "How a registered anchor kind is resolved" below. | COR-050 point 2 |
| `project_rule_set` | The one project rule set a capability declares, which its install creates ("The declared project rule set", in [`component-registry.md`, "Install pre-flight checks"](component-registry.md#install-pre-flight-checks) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->). `name` is the set's name. `inherits` is the name of one of the capability's own method sets, written bare. `scope` holds `types` alone, since a capability cannot know a project's paths. Each type is one the capability's own `friction.types` declares, written `<capability>:<type>`. `title` is one line for the created file's heading. All four are required. The packages check refuses an `inherits` that names no method set the capability ships under `rule-sets/`, or one whose version does not read. It also refuses a `name` one of the capability's own sets takes, a type the capability does not declare, and the key on an adapter. | COR-017 |
| `loaded_rules` | An adapter's alone. What it declares, and how the backbone renders the capabilities' rules index from it: [the adapters README, "How a capability's rules reach a session"](../adapters/README.md#how-a-capabilitys-rules-reach-a-session) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->. | COR-070 point 2 |

What holds across the table:

- **Two kinds of `schema_version`.** At the top level it versions the package file. Everywhere else it is the *point's* version, an integer from 1. Everywhere else means a data point, an offered point, a contribution, a subscription and a `depends-on` entry. Two versions are compatible when they are equal (COR-053 point 5).
- **Command references** are a path through the `commands:` tree, tokens separated by single spaces (`create page`), landing on a leaf that exists. They are `command` on an offered event, a contribution, a subscription, a validator entry or an anchor kind's entry, and a data point's `question`.
- **Paths** are relative, with no `..` segment: every `script`, `schema`, `docs.locations` path, `friction` place, held folder and surface entry, and every `footprint` and `runtime_ignore` entry. The repository check names the offending segment.
- **Role names and addresses are words.** Every part of a qualified role `<publisher>::<role>` and of a point address `<publisher>::<role>:<point>` is a word, `[a-z][a-z0-9-]*`. That holds in `connections.roles`, the keys of `accepts` and `offers`, a contribution's or subscription's `point`, and a generated `depends-on` entry's `process`. These are the words the configuration file's selection keys admit and the filler mapping below needs. The word is defined once, as the citation grammar's (COR-019).
- **Values are the point's.** A `default.value` or a contribution's `value` is any YAML the point's companion schema admits. The package schema does not type it, and the data point's resolution judges it ("How a data point resolves").

**Casing.** Two spellings meet in this file, and both stay.

- The keys that predate the connection-points record are snake_case: `schema_version`, `requires_backbone`, `requires_capabilities`, `runtime_ignore`. They are like the backbone's other YAML (the manifests above, and the schemas README, "YAML conventions").
- The compound keys COR-053 decides by name are kebab-case, `extension-points` and `depends-on`, written as the record spells them (COR-053 point 3).
- Every other key inside `connections`, `docs` and `friction` is a single word. `schema_version` keeps its snake_case there.

**A new key** is spelt as the record that decides it spells it. Where no record names it, it is a single word if one suffices. A compound is kebab-case inside `connections`, `docs` and `friction`, and snake_case at the top level, like the keys it sits beside.

**Note:** one near-collision to mind. The generated `depends-on` here is copied from the process definitions' `depends_on` (COR-038). It is one fact in two files, each spelt as its own record spells it.

### Validation: the package schema

Every `package.yaml` validates against one backbone file schema, `.pkit/schemas/backbone/package.schema.json` (Draft 2020-12). The class is described in the schemas reference's page on backbone files. The schema is read from the tree of the project being validated, never from a copy in the binary. So a tree recorded before it landed skips the shape checks and reports so.

Two callers run the validation on the same code: `pkit validate`, as its **`packages`** member, and the register pre-flight ([`component-registry.md`](component-registry.md#register-pre-flight-checks-incubated-cor-031) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->). The member checks every capability and adapter the backbone manifest registers. The pre-flight checks the one incubated capability about to be activated.

- **Two `schema_version` values are in use, and both are accepted.** No reader distinguishes the two, and both require the same fields. The dispatcher reads `commands:` from either. So the schema accepts `1` and `2` as an integer enum, and nothing is bumped or migrated. A third value is an error until a record introduces it.
  - **Version 1** is the scaffolded default.
  - **Version 2** marks the files that adopted the `commands:` block when COR-021 said the version bumps with it.
- **Known keys are strictly typed, and unknown keys are errors.** Every object the schema declares is closed (`additionalProperties: false`), at the top level and inside every block. So a key the schema does not know fails the shape check at that key. The decision, and what to do about such a key, is "Strict on unknown keys" below.
  - The message suggests the nearest known key (`unknown key 'foootprint'; did you mean 'footprint'?`), through the one renderer every backbone file schema shares.
  - Such a key fails `pkit validate` and refuses a register like any other error.
- **Repository checks,** all errors but the one below:
  - `component.name` equals the directory name.
  - `component.version`, `requires_backbone` and every dependency range parse.
  - Every command `script` exists.
  - A declared connection point sits under a role in `connections.roles`.
  - An accepted data point's (and an offered event's) companion `schema` exists under the capability's `schemas/`.
  - Every command a point or extension names exists in `commands:`.
  - Every command a validator names, every command filler a contribution names, and every resolver an anchor kind names, exists there and declares the query contract. A data point's question does not declare it.
  - A kind the backbone resolves itself (`path`, `record`, `artefact`) is refused at its `friction.kinds` entry.
  - A contribution names `command` or `value`, not both.
  - `docs.locations` paths, `friction` places, held folders and surface entries, and `footprint` and `runtime_ignore` entries are relative sub-paths, with no absolute path and no `..`. Every command `script` path is relative.
  - A `runtime_ignore` entry lies in its component's own folder, `.pkit/capabilities/<name>/` or `.pkit/adapters/<name>/` (ADR-009 rule 7).
  - A place's or held folder's `location` is a declared one. A held folder names one, holds no `**` and ends in no glob. A tree without the package schema gets these from this check.
  - An offered process point names a definition of the component, by its `id`. Its `schema_version` equals that definition's `interface.version` where the definition declares one. A difference is located at the point's `schema_version`, and names both values and both files (COR-053 point 5).
  - The generated `depends-on` list says exactly what the component's process definitions generate, marked `generated: true`. A stale copy is located at the list, or its nearest present parent. It says what is missing and what no definition declares, and names `pkit capabilities refresh <name>` as the fix.

  Those last two are the repository checks that read process definitions, through one walk of the component's `schemas/`.
- **One repository check warns:** a `runtime_ignore` entry that declares the process journals, in a project that commits its journals (`process.journal.committed: true` with `enabled: true`, COR-033 P7). An entry declares them when, read as a path, it matches the backbone's journal pattern.
  - The backbone owns that ignore line and drops it then, and its choice takes precedence. The render drops the component's entry too, and names it in a comment line of `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content -->. The render and the warning follow one rule.
  - The entry is the mark of a component older than the backbone it runs on. It is a warning, since the render has already neutralised it. While the journals stay ignored, the entry is redundant and not warned.
  - The fix it names follows where the package comes from: its registry `origin` and the ownership module's `is_synced_copy` (the lifecycle README, "The ownership predicates"):
    - a `kit-shipped` package in an adopter is a synced copy the next sync overwrites, so upgrade the component together with the backbone
    - an `externally-sourced` one is restored to its pin (COR-041), so move the pin to an author release that drops the entry
    - the project's own file, an `incubated-in-repo` capability or any other package in the methodology's source, drops the entry
- **One check across packages warns,** over the installed capabilities only: an `aliases` entry another name shadows.
  - The dispatcher gives a top-level name to a backbone command first, then to a capability's own name. Next it gives the name to the first capability in manifest order that declares it as an alias. The check reads the table that walk builds, the one the dispatcher binds. So it reports exactly the aliases `pkit <alias>` does not reach.
  - The warning is located at the entry. It names the alias, its capability and what holds the name. What holds it is the backbone command `pkit <alias>`, another capability's name, or the same alias of the capability that registered it first. So a generic alias (`analysis`) is never lost, or taken by a later capability, without a word.
  - A warning, not an error: the alias is a shorthand, and the message points at the canonical `pkit <capability> …`, which still works.
  - An alias that already reaches its own capability, its own name or its own alias repeated, loses nothing and is not reported.
- **One check across packages fails,** over the installed capabilities only: a capability that surfaces a namespace under a name a backbone command holds.
  - The dispatcher gives the top-level name to the backbone command, so `pkit <capability> …` runs that command and never reaches the capability.
  - The check reads the capabilities the dispatcher builds groups for, those whose package declares a `commands:` block. It reads them against the backbone's commands as the dispatcher has them when the check runs, never a list kept by hand.
  - An error, not a warning: unlike an alias, the name is the capability's canonical form. The error is located at `component.name`, and names the rename that lasts for where the package comes from, as for a reserved name below.
  - The backbone gains commands with its releases, so an upgrade can take a name that was free when the capability shipped. `pkit new capability` refuses such a name, while `capabilities install` and `register` do not.
  - A capability with no `commands:` block surfaces no namespace and is not reported.
- **One check of the registry fails:** a component registered under a name the lifecycle reserves for its kind.
  - **For a capability:** `core`, `project`, `adr` and `backbone`, the names `pkit new capability`, `capabilities install` and `capabilities register` refuse.
  - **For an adapter:** `backbone`, which `pkit new adapter` refuses, as `pkit init` refuses a source that ships an adapter under it. Such an adapter's changesets and validators would be read as the backbone's, the two places the backbone's name is read beside an adapter's.
  - The capability-only names collide where only a capability's name is read, so an adapter may take them.
  - One registered before its name was reserved stays registered, since nothing unregisters it. So this check is where it surfaces.
  - The error is located at `component.name`, gives the reason the refusal gives, and names the rename that lasts. For a capability, the rename follows where the package comes from:
    - the project's own capability is unregistered with `pkit capabilities uninstall <name>`, which keeps an authored capability's files. It is renamed (its directory and `component.name`) and registered again under the new name.
    - a package a sync restores is its author's to rename, and is uninstalled until it ships under another name
  - An adapter, which no verb unregisters, is renamed where it is authored: its directory, its `component.name` and its entry in the backbone manifest's `components`. One a sync restores is the methodology source's to rename.
- **Another check of the registry fails:** an adapter and a capability registered under one name.
  - **The reason:** the backbone reads a component by its name alone where it reads both kinds.
    - A changeset names its component, and the release keys every `package.yaml` under `.pkit/` by name, so a release would move only one of the two.
    - Every registered component's validators are owned by its name, so the two would share one owner.
    - The wiring resolver reads the component registry by name, so one of the two would be read under the other's kind.
  - **So the second of the two is refused** wherever a component is named into a project:
    - `pkit new adapter` refuses a name a capability holds.
    - `pkit new capability`, `capabilities install` and `capabilities register` refuse a name an adapter holds.
    - `pkit init` refuses, before writing anything, a methodology source that ships an adapter and a capability of one name.

    A component holds its name when the backbone manifest registers it, or when its directory exists under `.pkit/adapters/` or `.pkit/capabilities/`.
  - A pair registered before the refusal stays registered, since nothing unregisters either. So this check is where it surfaces.
  - The error is located at each one's `component.name`, and gives the reason the refusals give. It names that one's rename, as for a reserved name above. Renaming either clears both.
- **One check across packages fails,** over the installed capabilities only: a folder of held documents that oversteps its bounds ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 1).
  - **It oversteps them when it:**
    - equals or encloses a documentation root
    - equals or encloses any declaration's place, its own component's included, since that would empty the place
    - shares a file with another component's held folder, or with a rule-set folder
    - equals, encloses or lies within another of its own component's held folders
  - The error is located at the `friction.held` entry and names each bound it oversteps.
  - The error is read from friction discovery's one judgment of the folder, which leaves such a folder holding nothing. So its files stay artefacts of the places matching them.
  - One component holds each held file, and rules stay artefacts (COR-051 point 2). Two components' folders sharing a file are refused at both entries.
  - The folder, or glob of folders, is judged on its declaration, never on which files exist.
  - **Two precedences** settle the files a held folder shares without overstepping a bound:
    - **A held folder wins over the places.** A place that only shares some files with it leaves those files to it. The place may be the project's or a root, another component's, or its own component's, such as a glob reaching into the folder. No place reads such a file as an artefact.
    - **Within one component, the first declared held folder wins.** Two of a component's held folders may share files without either lying within the other, such as `revalidations` and `*/revalidations`, which both reach `revalidations/revalidations/`. Each shared file is held for that component either way, by the folder it declares first.
- **Three checks across packages report and do not fail,** over the installed capabilities only. Each is a type finding that artefact discovery raises and names the `packages` check to report ([COR-056](../decisions/core/COR-056-artefact-types.md) point 3). None of them fails:
  - a place naming a type its own `friction.types` does not declare, at the place's `type`. The place gives no type.
  - a tie between places only components declare: typed places that rank equal on a file and give it different types. It is reported at each tied place, and the artefact counts as each type.
  - one capability's typed place taking precedence over another capability's own place that is not root-wide, at the typed place. Its type stands.
- **One more check across packages fails,** over the installed capabilities only: an anchor kind two or more of them register under `friction.kinds` ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 2).
  - The error is located at each one's entry, naming the others.
  - No registration wins: the kind is refused for every registrant, and an anchor of it is unresolved until one registration remains.
  - The error is read from the one anchor-kind registry, so what is reported is what an anchor of the kind meets.

The other checks *across* packages are the wiring resolver's ("How the wiring is resolved" below): roles, points, mandatory marks, cycles, fingerprints and the version relations. `pkit validate` runs them as its `connections` and `versions` members. The register pre-flight runs the same resolution.

### Strict on unknown keys

**The rule.** Package metadata is strict: a key the package schema does not know is an **error**, wherever it is written. It is an error at the top level, and inside a component, a command leaf, a validator entry or a dependency. It is one in any part of the `connections`, `docs` and `friction` blocks too.

[COR-053](../decisions/core/COR-053-connection-points.md) left whether unknown keys become errors to this specification, as a surface change of its own if taken (its Implications, "Schema changes"). This is that decision.

**What an adopter sees, and does.**

- *With only kit-shipped components, nothing.* Every shipped package validates, and the sync that brings the strict schema brings the packages with it.
- *With a package of their own*, an incubated capability (COR-031) that carries a key the schema does not know, `pkit validate` fails under `packages`. It names the file, the key and the nearest known key (`.pkit/capabilities/<name>/package.yaml:/foootprint → unknown key 'foootprint'; did you mean 'footprint'?`). `pkit capabilities register` refuses the capability with the same message. The fix is in the adopter's own file: rename the key to the one suggested, or delete it.
- *A package missing a required field*, `schema_version`, `description` or `requires_backbone`, is refused the same way (`'description' is a required property`). The fix is to add it: `schema_version: 1`, a one-line summary, a version range. The capability scaffold has always written all three.
- *A tree not yet synced* keeps its own, permissive copy of the schema, and that copy is the one applied. There an unknown key still only warns, with the same sentence, until the sync.

**No version bump and no migration.** The flip changes no key and no meaning. A file that carried only known keys and COR-017's fields validates as before, so the package file's own `schema_version` stays at `1` and `2`. The one shipped file that had to change, the `claude-code` adapter's package, gained its `description`, and the same sync that delivers the schema replaces it. The finding names the fix, in place of a migration guessing it.

### The connection, documentation and friction blocks

Three optional blocks carry what the newer core records ask a component to declare. The key names each record decides are used as written. The layout beneath them is this reference's ("Field layout and casing" lists every key). `pkit::` in the example is this distribution's publisher qualifier ("The methodology's literals", below).

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
        question: ask readers                      # optional: its command that asks the person (COR-061)
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
    - { location: logs, path: "*/reviews" }        # or a glob of folders, its last segment plain
  surface: ["src/**"]                              # repository-relative globs
  kinds:                                           # an anchor kind, and the leaf that resolves it
    source: { command: resolve source }            # the leaf declares `query-contract: true`
```

`depends-on` is the one block a person never writes. **`pkit capabilities refresh <name>`** regenerates it from the `depends_on` the capability's process definitions declare (the process area's connections page, "depends_on"). The refresh marks it `generated: true`, leaving the rest of the file as written. With nothing to generate, it removes the list, and any `extensions` or `connections` block the removal empties.

What each part of the backbone does with the list:

- the schema fixes the shape and the mark
- the packages pass compares the list with what the definitions generate, and fails a stale copy, naming the refresh. The definition always wins.
- the wiring resolver reads the entries and never opens a definition
- the capability lifecycle reads their `mandatory` marks ([`upgrade-flow.md`, "Mandatory process connections"](upgrade-flow.md#mandatory-process-connections-cor-053-point-6) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->)

Refresh is authoring-time. It runs where the capability is authored: the methodology's source for a kit-shipped capability, the adopting project for an incubated one (COR-031). It refuses a kit-shipped capability installed in an adopting project, whose package file is core-owned and overwritten by sync. A stale copy there is the capability author's defect, reported upstream.

### The methodology's literals

Three names the core records need are written record-neutrally, and the literal is left to the distribution's reference ([COR-053](../decisions/core/COR-053-connection-points.md), the vocabulary paragraph of its Decision). This is that reference. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The publisher qualifier the methodology reserves for the roles it defines, written `<methodology>::` (COR-053 point 1) | **`pkit::`** | Role names (`pkit::documentation`) and point addresses (`pkit::documentation:readers`). In the `connections` block above, and in the configuration file's `connections.providers` and `connections.selections` keys. And as a role block's key where the qualified form is needed. |
| The one front-matter key "owned by the methodology, named for it" (COR-053 point 10) | **`pkit:`** | An artefact's front matter, or a collection entry: the container (the schemas reference's page on backbone files, "The container", and `backbone/container.schema.json`). |
| "a sub-path the backbone owns for slot files", under the internal documentation root ([COR-052](../decisions/core/COR-052-slots.md) point 2) | **`pkit/fillers/`** | The prefix of every project filler file ("Where a project filler file lives: the address-to-path mapping", below). |

- **The qualifier names who defined a role, never who implements it** (COR-053 point 1). A third party coins its roles under its own name: `super-docs::documentation` is a different role that shares a word with `pkit::documentation`. A third party may also *provide* a `pkit::` role, interchangeably with the capability that first defined it. But it never coins a role under `pkit::`.
- **Project-published roles have no qualifier yet.** COR-053 leaves them to a later refinement.
- **The container key is not a qualifier**: an artefact has one `pkit:` key whoever published its roles. A third party's role block sits inside it, beside the methodology's own blocks (COR-053 point 10).

These strings are this distribution's choice, not a principle: another distribution of the same records could choose others. Changing one would change files adopters have written, so it would be a surface change shipping a migration (COR-010), not a record amendment.

**Four more literals, for the commands the backbone runs.** The literals of the query-contract declaration and of the offline marker are left to this reference. They were specified with the first query commands that run: the validators by which a component joins validation ([COR-055](../decisions/core/COR-055-validation.md) point 3).

The deadline every run tells its command is named here too. So is the declaration of what a command filler reads beyond the working tree, which [COR-052](../decisions/core/COR-052-slots.md) point 6 has its capability declare. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The one constant declaration that a command honours the query contract — bounded, deterministic, read-only, needing no network (COR-050 point 2) | **`query-contract: true`** | On a `commands:` leaf, beside `script` and `help`. Required on the command a validator names, which validation runs as a query (COR-055 point 3). Required on a command filler and on an anchor kind's resolver too. The `packages` member reports one without it. The runner — the validator registry, the data points' resolution, the anchor-kind registry the friction checks and rule-set validation read — refuses to start such a command. |
| The offline marker, by which a well-behaved command can tell that it runs offline | **`PKIT_OFFLINE=1`**, with **`UV_OFFLINE=1`** beside it | The environment of every query command the backbone starts — validators, command fillers and anchor-kind resolvers. `PKIT_OFFLINE` is what a command reads. `UV_OFFLINE` is honoured by `uv`, so a script with a `uv run --script` shebang resolves its dependencies from uv's cache and never fetches. |
| The deadline every run tells its command | **`PKIT_COMMAND_DEADLINE`**, seconds since the epoch, to the millisecond | The environment of every command the backbone's runner starts — queries, predicates and the report's context read alike. A command may read it to know by when anything it starts must have ended ("A run inside a run" below). **`PKIT_COMMAND_STRAYS`**, set beside it, and **`PKIT_RUN_CACHE`**, set for the length of a `pkit validate` run, are the runner's own: no command reads or sets them. |
| Which state a command filler reads beyond the working tree — history, settled state, or both (COR-052 point 6) | **`reads:`**, a list of **`history`** and **`settled`** | On a command filler's `commands:` leaf, beside `query-contract: true`. `history` is the current history, read at HEAD. `settled` is the default branch as the backbone resolves it, never a base named for one run. Absent, the working tree only. The schema refuses any other value, an empty list and a value twice. The `packages` member refuses a leaf that declares it without `query-contract: true` ("How a data point resolves"). |

**How dependencies are provisioned before an offline run.** A query declares that it needs no network and runs offline-marked. So a script's dependencies must already be in uv's cache when it runs.

- **`pkit init` and `pkit sync` put them there,** as one of their steps (self-host included).
- **`pkit capabilities install`, `register` and `upgrade`** run the same step for the one capability they bring in.
- **What the step resolves:** each command a registered component — capability or adapter — declares with `query-contract: true`, whose script carries inline script metadata (a `# /// script` block). The step resolves that script's environment once, online, with uv's own resolution. It runs `uv sync --script <script>`, which resolves the metadata and installs the environment into uv's cache **without running the script**.

The step prints one line per query command:

| Line | When |
|---|---|
| `provisioned` | the script did not resolve offline, and resolved online |
| `unchanged … already provisioned` | the script resolves offline — the condition the query meets — so nothing is fetched: the step is idempotent, and a re-run resolves nothing |
| `skipped … nothing to provision` | the script declares no inline dependencies (or does not exist — the `packages` member reports that) |
| `warning … not provisioned` | the script resolved neither offline nor online — no network, no `uv` on the PATH — with uv's reason. **Never a failure**: init and sync go on and keep working offline |

A dry run asks uv nothing and prints `would provision` for each script with inline dependencies. Provisioning happens outside the bounded run: it sets no offline marker and is not bound by the command bound. A pipeline runs `pkit sync` on checkout, before its gate.

A query whose environment is not provisioned exits with uv's report that a dependency is not in its cache and the network is disabled. The query policy recognises it on standard error and names it, rather than reporting the exit: **"environment not provisioned — run `pkit sync`"**. It is an error finding for a validator, and the reason an inert filler gives for a command filler. It is distinct from a command that answered nothing.

**Two more, for recognising the methodology's source repository.** The source repository is the one whose `.pkit/` is the methodology's own tree. Code that must recognise it without knowing which code runs does so by the package source beside the `.pkit/` tree at the repository root. The package's path, and the path of the dispatcher the router execs there, are this distribution's names. In this distribution:

| In the records | Here | Where it is written |
|---|---|---|
| The marker that recognises the source repository on the tree's side | **`src/project_kit/__init__.py`** beside the **`.pkit/`** tree. The in-tree dispatcher **`.pkit/cli/pkit`** is what the router's first route execs, not a marker. A checkout whose dispatcher was deleted is still the source, and the dispatcher is reported missing | Nowhere by a project. They are read at a repository root by the entry-point router's first route, and by the ownership predicate (`is_methodology_source`, the lifecycle README, "The ownership predicates"). Both copies cite this table. |

An adopter has the dispatcher but never the package source. Unlike the literals above, no project writes these, so changing them means changing the two copies together, not migrating an adopter's files.

### How a registered command is run

The backbone runs the commands a component registers through one runner: one lookup and one bounded run, with a policy per kind of command. The kinds share one command runner ([COR-053](../decisions/core/COR-053-connection-points.md) point 11).

- **The lookup.** A command is a leaf of the `commands:` tree ("Field layout and casing" above). One walk reads the tree: a command reference — a path of tokens — names a leaf through it. These all read the tree this way, so each resolves a leaf to the same script:
  - the dispatcher (`pkit <capability> <command>`)
  - package validation
  - the validator registry
  - the anchor-kind registry
  - the process engine's predicate runner
  - the report builder (`pkit report`, asking the project-management capability for the workstream)

  A process predicate's `run:` names a leaf by its own name rather than its path (the process README, "The predicate runner").
- **The run.** The leaf's script is started and read by these rules:
  - **How it starts:** with an explicit argument list, never a shell string, from the project root. It runs in its own process group, or inside another run in the outermost run's ("A run inside a run" below).
  - **What is captured:** standard output and standard error. Standard output is the answer, one JSON document and nothing else unless the policy reads it as text. Standard error is diagnostics.
  - **The bound:** the run is **bounded by thirty seconds**, a fixed backbone constant, not a setting. The one exception is an agent run, whose bound is the run's own limit and thirty seconds more (the agent-run row below).
  - **Past the bound:** exceeding the bound **kills the whole process group**. A script with a `uv run --script` shebang starts its interpreter as a grandchild, which killing the script alone would leave running. An interrupt of `pkit` itself kills the group too.
  - **Never an answer:** a run that does not start, exits non-zero, overruns, or prints anything but the answer its policy reads. What it is instead is the policy's.
  - **What a report of such a run shows:** where a policy reports such a run, it names how the run ended. It may show what the command wrote on standard error, never the stream whole. It shows only the last 10 non-blank lines, and at most 1500 bytes of them, every terminal escape sequence and control character removed.
- **A run inside a run.** A command the runner starts may start `pkit` again, and the tree keeps one deadline and one kill. For example, a validator reads a point through `pkit connections resolve`, which starts the point's command filler, and that filler reads the artefacts through `pkit friction artefacts`.
  - **The deadline:** every run tells its command, in its environment, **`PKIT_COMMAND_DEADLINE`** ("The methodology's literals" above). It is seconds since the epoch by which anything the command starts must have ended. It is the run's own end less two seconds, the time the command keeps to answer after something it started ran out.
  - **When a run is nested:** a run is **nested** when it runs inside a live run, that is, when all of these hold:
    - its environment carries a deadline
    - its process is in the process group that leads its session, as every process the outermost run's command starts is. That command leads a session of its own, and a command started from a terminal is not in such a group.
    - the directory the outermost run made and named in **`PKIT_COMMAND_STRAYS`** still exists, which it does only while that run's command runs

    A variable left over in a shell, or outliving its run, therefore never makes a plain `pkit` nested.
  - **How a nested run is bounded:** by the time remaining, rounded down to a tenth of a second and never more than its own bound. With none remaining, its command is not started, and the no-answer says so. A nested run starts its command in the outermost run's process group, rather than a session of its own. So the outermost run's kill, at its deadline or on an interrupt, reaches everything the tree started.
  - **Which command a no-answer names:** each level's deadline comes before its caller's. So the command that overran is the one a no-answer names, with the bound it had.
  - **A bound its caller left:** when that bound was the time its caller had left, rather than its own bound, the no-answer says so. An example is "did not answer within the 0.4 s its caller had left". A caller with more time might have had an answer.
  - **Strays.** A nested run cannot kill a group it shares with its callers. So when its command overruns, the nested run kills that command alone, and what the command started is left to the outermost run.
    - **The marker:** each nested run keeps a marker in the outermost run's directory, from just before it starts its command until the command ends by itself.
    - **A marker left behind:** a nested run leaves its marker behind when its command overran or was interrupted. It does too when anyone else killed its own process, such as a `subprocess.run(timeout=…)` in a validator, the operating system's out-of-memory killer or a `SIGTERM`.
    - **The sweep:** when the outermost run's command ends, however it ended, a marker left behind makes the outermost run end everything left in its group. The outermost run then removes the directory.
    - **No marker left:** nothing is swept. A group whose nested runs all ended by themselves is left as a run outside any other leaves it. So a process a command leaves running on purpose is not ended.
  - **What this does not cover.** The kill reaches only the group:
    - **A process that leaves the group escapes the kill:** one that starts a session of its own (`setsid`) or a group of its own. GNU `timeout` without `--foreground` starts a group of its own, and so does a shell with job control.
    - **A `pkit` started under such a process** runs outside the outermost group too. Under a new session, it runs with the deadline it inherited. Under a new group, it runs as a run of its own, with thirty seconds and a kill of its own. **In a script a query runs, do not wrap `pkit` in anything that makes a new session or group.**
    - What a killed nested command started runs on until the outermost run's command ends, not only until the nested run's deadline.
    - A marker cannot be written when the directory cannot be written to. Such a marker leaves those strays running past the outermost run's answer, when that run answers in time. Only the outermost run's own kill, at its deadline or on an interrupt, reaches them. When the outermost run cannot make its directory at all, the runs under it are not nested: each runs as a run of its own.
    - The deadline is written on the wall clock, and each run's own bound is measured on the monotonic clock. A clock step between a run and one nested under it shifts the nested bound by the step, never beyond thirty seconds. A time synchronisation is such a step, and so is the machine sleeping. The outermost run's kill is never late.
- **A tool the backbone runs itself.** The landing module asks `gh` of the hosting service, for `pkit pull-request` and `pkit release merge`. `gh` is not a registered command and has no answer policy: the module reads what it printed.
  - **How it starts:** through the same runner's one bounded start for a tool. It starts with an explicit argument list, from the directory the request acts in, and with nothing on standard input.
  - **Its group:** `gh` runs **in the caller's process group**, never a session or group of its own. So whoever ends the group `pkit` runs in ends a `gh` in flight too.
  - **Its bound:** the module bounds each call, a reading or a request (the CLI README, "Pull-request commands"). On overrun, or an interrupt, the tool **alone** is ended: asked to stop, then killed two seconds later, its pipes closed unread. The group is its caller's, so the group is never signalled.
- **Provisioning, before any run.** A query runs offline-marked and fetches nothing, so the environment its script needs is prepared beforehand, not by the run. **Provisioning is a step of `pkit init` and `pkit sync`**, which resolve every registered query command's environment once, online. So is each capability verb that brings a capability in, for that capability's commands ("How dependencies are provisioned before an offline run" above). A query whose environment is not provisioned gives the no-answer "environment not provisioned — run `pkit sync`".
- **The policies.**

  | Policy | Run by | Arguments and environment | The answer | No answer is |
  |---|---|---|---|---|
  | predicate | the process engine, for every predicate a process definition declares | the subject and `--json`. The environment unchanged but for the run's deadline. A predicate may reach the network. | a JSON object the engine interprets (the process README, "The predicate runner"). | indeterminate, fail-closed: a gate stays shut — the reason naming how the run ended, with the tail of what the predicate said beside it. |
  | query | `pkit validate`, for a component's validator, a query with no subject (COR-055 point 3). | `--json`. The offline marker set ("The methodology's literals" above). The base override (`PKIT_CHECK_BASE`) and the change's own head (`PKIT_CHECK_HEAD`) removed. A validator answers about the project's state, never about a base named for one run (COR-055 point 2). The leaf must declare `query-contract: true`, or it is not started. | the findings document (the `validators` row above). | an error finding naming how the run ended (COR-055 point 6). For an exit, it comes with the tail of what the command wrote on standard error. Its lines are joined on the finding's one line. |
  | query, for a filler | the data points' resolution, for a contribution's `command`. Read by `pkit validate` and `pkit status`, and by `pkit connections resolve` for its one point's fillers only. | `--json` alone: a filler takes no parameter ([COR-052](../decisions/core/COR-052-slots.md) point 6). The offline marker set, and the base override and the change's own head removed, whichever command started the resolution. A filler reads state, never a base named for one run (the same point). The leaf must declare `query-contract: true`, or it is not started. A leaf that declares it reads settled state is not started while the default branch resolves to no commit ("How a data point resolves"). | the filler envelope, `{"schema_version": <the point's version>, "value": <the point's value>}` and nothing else — no `remove`, which is the project's alone — whose value fits the point's schema whole. | the filler inert, never an empty or a partial value: the point follows its inert policy ("How a data point resolves"). The inert reason names a run that gave no answer as the validator's finding does. |
  | query, for a resolver | the friction checks and rule-set validation, for an anchor (or a cited source) of a kind a capability registers. Once per anchor value for a run, and not again in it once it overran its bound ("How a registered anchor kind is resolved" below). | `--json`, the end-of-options marker `--`, then the anchor value, its one subject ([COR-052](../decisions/core/COR-052-slots.md) point 6). The value comes last, so that no value is read as an option. The offline marker set, and the base override and the change's own head removed. The leaf must declare `query-contract: true`, or it is not started. | `{"paths": [...]}` and nothing else: the files the anchor stands on, in the state the check reads. | the anchor unresolved, never resolved, and never dead. The change check fails on it and its artefact is not judged (`no-answer`). A cited source fails rule-set validation (`unanswered-source`), the reason naming the run as the validator's finding does. |
  | context read | `pkit report`, for the workstream on a report's context line. | none. The environment unchanged but for the run's deadline — the verb asks the tracker. | the value it prints, read as text rather than parsed: the verb prints it bare, not as a JSON document. Output that is not UTF-8 is no value. | the workstream omitted, silently where the verb is absent or printed nothing. Where the verb failed, the report names how it ended in a warning, with the tail of what it wrote on standard error. The verb failed where it did not start, exited non-zero, overran, or printed output that is not UTF-8. The report then goes on without the workstream. |
  | agent run | `pkit agents run`, for the runner an adapter registers. | none, and the run's request on standard input. The environment unchanged but for the run's deadline. A confined run's runner is the one its clone registers, run from the clone's root with `PYTHONDONTWRITEBYTECODE=1`. So no import leaves a cached file in the clone that the check after the run would read as a change. Bounded by the run's limit and thirty seconds more, the time the runner keeps to end the harness and answer. On overrun, or an interrupt, the runner is asked to stop with `SIGTERM`, and is killed two seconds later. Inside another command's run it is refused before anything else: that run's kill asks nothing first, so the harness would outlive it. | the runner's answer, the document [the adapters README, "The agent runner"](../adapters/README.md#the-agent-runner) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> specifies. | a run with no answer (`no-answer`), the reason naming how the runner ended and the last line it wrote on standard error. A runner that cannot start is `not-started`, and one past its bound is `timed-out`. |

  The report builder is bounded like every other run, not exempt.

  A subscriber's policy arrives with the events that run subscribers ([COR-053](../decisions/core/COR-053-connection-points.md) point 9 sets its limits).
- **The seams back: what a script reads from the backbone.** A component's script runs in its own environment and never imports the backbone. What it needs of what the backbone computes, it reads through the backbone's reading commands, never by computing it again. Each prints one stable JSON document:

  | Reading command | What a script reads it for |
  |---|---|
  | `pkit connections resolve <address> --json`, [its section](../cli/README.md#connections-resolve-address---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> | one data point, as it resolves ("Reading one point from a script" below) |
  | `pkit friction artefacts --json`, [its section](../cli/README.md#friction-artefacts---at-rev---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> | where the artefacts are |
  | `pkit repository base --json`, [its section](../cli/README.md#repository-base---base-ref---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> | settled state, and the history at hand |
  | `pkit rule-sets reach --json`, [its section](../cli/README.md#rule-sets-reach-path---at-rev---preview---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> | which accepted rules bind on each artefact ([COR-051](../decisions/core/COR-051-rule-sets.md) point 7) |
  | `pkit rule-sets altered --json`, [its section](../cli/README.md#rule-sets-altered---base-ref---head-rev---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> | what a change altered or brought under a rule, and the rules on each |
  | `pkit capabilities project-rule-set <name> --json`, [its section](../cli/README.md#the-project-rule-set-a-capability-declares) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle --> | the project rule set an installed capability declares. A capability's migration reads it for an earlier install ([`component-registry.md`, "The declared project rule set"](component-registry.md) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->) |

  - **What a query may call:** each reading command is read-only and needs no network, so a query may call it.
  - **What the script does itself:** the script applies the answer itself. For example, the living-docs validator decides which of two places matching a file wins, and which space it serves.
  - **What the script never does:**
    - re-read the declarations, list the working tree or match a path against a place
    - resolve a reference or compute a merge-base
    - walk a route to a rule set or judge a pin
  - **What a filler may call:** the artefacts, rule-set and settled-state readings resolve no data point. So a filler may call them while a point it contributes to resolves. A filler never asks for a point.
  - **The bound:** a query that calls a reading command keeps the reading inside its own bound. A filler the reading starts inherits the query's deadline and the outermost run's process group ("A run inside a run" above). Inside `pkit validate`, a point the run has already resolved is read from its run cache ("Reading one point from a script" below).

The dispatcher's proxy is not a run in this sense. `pkit <capability> <command>` is a person's focused surface, so it takes the lookup, inherits the terminal's streams, and is neither bounded nor captured. A data point's question runs through the same proxy run, since a person answers it ("A data point's question", below).

### How a registered anchor kind is resolved

A capability registers an anchor kind under `friction.kinds` ("Field layout and casing" above). The backbone runs the leaf as a query ("query, for a resolver" in the policies above). [COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 2 sets the contract: the time bound, the obligations the capability declares, and failing closed. The answer's shape is left to this reference.

**The answer** is `{"paths": [...]}` and nothing else:

- `paths[]`: each entry is a repository-relative POSIX path naming a file of the state the check reads. That state is:
  - the working tree's one listing, for the change check and for validation
  - the named commit's files, for the change check with `--head <rev>`
  - HEAD's files, for the whole-repository check and the commands that read HEAD
- A path named twice counts once, and order does not matter.
- An empty list is an answer: the value denotes nothing, and the anchor is dead.
- An answer file it names is left out, since no anchor stands on one (COR-062 point 2). So an answer that names only answer files leaves the anchor dead, reported as `its resolver names only answer files (<n>), on which no anchor stands`.

**What the answer must name.** Every file whose content decides what the value denotes:

- the file or files the thing is kept in
- any file that maps the value to them, such as an index, a registry or a table of contents

The engine sees a change only as a change to the content of a file the answer names. So a file left out is a change nobody is asked about.

- **A thing kept outside the repository,** such as a standard a page quotes, has no file of its own. So its kind answers the file that stands for it in the repository. Its capability keeps in that file only what should count as the thing's change. The engine reads the file's history, never the thing (living-docs' `source` kind is one).
- **A file a place holds** is read by its content, as an artefact is ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 5). So nothing in its `pkit` container decides what a value denotes.
- **A kind is one word for the whole project,** and a second registration refuses it for both. So name a kind for what its resolver finds.

**What the engine cannot see**, whatever the answer names:

- a file that leaves the answer (one of several removed, or a mapping repointed to a file that did not change). The engine sees such a change only where a file the answer still names changed in the same commit, as a named mapping file does.
- a resolver that answers differently because its own code changed
- in the change check, what the anchor stood on at the base

It is also coarser than the thing itself. Any change to a named file's content or mode counts, as for a path anchor. A shared mapping file, once named, asks every anchor that maps through it whenever it changes.

A capability keeps all of this small by its layout: one value, one file, found from the value itself (`sources/<value>.md`). Then a change to the thing is a change to that file, and removing it leaves the anchor dead. No shared file stands between a value and its file.

**How it is asked.** The leaf's script is started with `--json`, `--` and then the value. So a value that begins with a dash is read as the value and never as an option.

- **What a resolver needs:** no history, no points and no knowledge of the engine. It reads the files on disk alone, takes one subject, and cannot read the project at an older commit.

- **A value the system cannot pass as an argument** (one holding a NUL byte) is not started, which is no answer.
- **Against HEAD:** the resolver reads the files on disk whichever check asks. The whole-repository check and the commands that read HEAD then read its answer against HEAD's files. So a path only uncommitted work holds is no answer there. The report's uncommitted-paths line says how much HEAD does not hold.
- **With `--head <rev>`:** the change check reads a commit that need not be on disk. So it runs a resolver only where the working tree is that commit: HEAD at it, nothing uncommitted. There it reads the resolver's answer against the commit's files. Elsewhere it refuses rather than read the disk as the commit, naming the anchor and the checkout to run from (the CLI README, "friction check").

**What the checks do with it.**

- The change check asks an artefact when the diff changed the content or mode of a file the answer names, its own file left out. A pure rename keeps the content. A write to the `pkit` container alone, of a file a place holds, changes nothing.
- The whole-repository check finds the anchor stale where such a file's content or mode differs between HEAD and the revalidation point, renames followed. The stale anchor is dated from the oldest change to that file that no commit put back since. An edit put back is no change.
- The files count as anchored for the uncovered-surface measure.
- `friction.exclude` does not apply to the files an answer names. An anchor of a registered kind names what it stands on by its value, as a record anchor does. Exclusions cover paths ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 7).
- Each anchor value is resolved once per check, however many artefacts carry it. A resolver that overruns its bound is not started again in that check. The values it had left have no answer, so a resolver that hangs costs one bound, not one per value.

**Failing closed.** A resolver gives *no answer* when it:

- exits abnormally
- overruns its bound
- runs in an environment not provisioned
- cannot be started
- prints anything that is not exactly the answer
- names a path the state the check reads does not hold

No answer is never an answer naming nothing. The anchor is reported as having no answer (`no-answer`), not as dead, and whether what it denotes changed cannot be told.

- **A kind nothing may resolve is refused before any run:**
  - one no installed capability registers
  - one two register
  - one whose command names no leaf of its `commands:` tree or lacks the declaration

  Its anchors are `unresolved-kind`.
- **The change check fails what it can lay at the pull request** ([COR-050](../decisions/core/COR-050-anchors-and-friction.md) point 12). A resolver is asked about the head alone. So the check knows whether the diff added an anchor, and whether the base could resolve its kind, and nothing else about the base. The base's registrations are read from the base commit.

  | At head | The diff | Finding | Fails in enforcing mode |
  |---|---|---|---|
  | the kind cannot be resolved | added the anchor | `unresolved-kind` | yes |
  | the kind cannot be resolved | kept the anchor, and the base could resolve the kind. The diff uninstalled the capability, added a second registrant, or dropped the declaration or the command | `unresolved-kind`, "this diff took its resolver away" | yes |
  | the kind cannot be resolved | kept the anchor, and the base could not resolve the kind either | none: the whole-repository check reports it | no |
  | the resolver names no file | added the anchor | `dead-anchor` | yes |
  | the resolver names no file | kept the anchor | `dead-unattributed`: whether the diff removed what it denoted cannot be told, and the whole-repository check reports it as dead | no |
  | the resolver gave no answer | added or kept the anchor | `no-answer`: the check could not tell whether the diff changed what the anchor denotes. A second run may clear it. If it does not, run `pkit sync`, or the resolver needs mending | yes |

  - **What passes:** a pull request that deletes what a kept anchor denotes passes the change check. The whole-repository check reports the anchor dead after the merge. This is the third limit above, stated rather than guessed at.
  - **What fails:** a missing answer is different in kind: the check did not do its work. So it fails, and a failure of that kind costs a second run.
- **An artefact with an anchor that cannot be resolved is not judged.** In the whole-repository check, `friction explain` and `friction debt`, these leave the artefact's state `unresolved`:
  - an anchor whose kind nothing may resolve, which is `unresolved-kind`
  - an anchor whose resolver gave no answer, which is `no-answer`

  The state `unresolved` is never `current`, and comes ahead of `stale`, though what the artefact's other anchors owe is still listed.
  - **`friction record-status` refuses such an artefact,** as it refuses an artefact whose points lie beyond a shallow clone.
  - **A reader of the machine-readable documents** treats `unresolved` as not judged, never current. How it treats a state it does not know is the CLI README's ("Friction checks"). It reads the anchor's finding where its rule differs by cause:
    - a missing answer is a check that did not do its work
    - an unresolved kind is a declaration to mend, failed only by the change check and at the registration
  - **An anchor whose resolver names no file is dead.** Its artefact is judged on its other anchors, as for a dead anchor of any kind.

**Rule-set sources.** Rule-set validation resolves a cited source the same way (the schemas README, "Rule-set files"). A source whose resolver names no file is an error, `missing-source` ([COR-051](../decisions/core/COR-051-rule-sets.md) point 5). So is one whose resolver gives no answer, `unanswered-source`: a resolver that ran and gave no answer has not resolved the source. Only a source kind with no resolver that may run is reported rather than failed.

**Provisioning.** A resolver's leaf declares the query contract. So `pkit init` and `pkit sync` provision its script as they provision a validator's ("How dependencies are provisioned before an offline run" above).

### Where a project filler file lives: the address-to-path mapping

A project answers a data point with a file of its own (COR-052 point 2). The file's location is **derived from the point's address, never declared**. The location rule binds the file to the backbone's filler schema by that path.

The mapping must be **path-safe** and **injective on valid addresses**. This section defines the mapping and its inverse.

**Valid addresses.** A *word* matches `[a-z][a-z0-9-]*`: a lowercase letter, then lowercase letters, digits and hyphens. A valid address is `<publisher>::<role>:<point>` with each part a word — the grammar `config.schema.json` applies to the keys of `connections.providers` and `connections.selections`. Because `:` is not a word character, a valid address splits into its three parts in exactly one way. The package schema applies the same grammar to every address a package declares ("Field layout and casing"), so every declared point has a filler path.

**The mapping.** One directory per address part, the point as the file name:

```
<publisher>::<role>:<point>   ↦   <internal-root>/pkit/fillers/<publisher>/<role>/<point>.yaml
```

`<internal-root>` is the internal documentation root: `docs.internal` in the configuration file, default `docs/`. The prefix `<internal-root>/pkit/fillers/` is a documentation location derived like any other, so COR-049's rules apply to it ([COR-049](../decisions/core/COR-049-documentation-roots.md) points 4 to 6). A location is recorded when a command first places a document there, so that a root changed later moves nothing already placed.

No command places a filler yet: a project writes its filler files itself. So nothing records the prefix, and it is derived from the current root on every read. After changing `docs.internal`, move the filler files with it. The command that writes a filler, when one ships, records the prefix on first use.

The mapping fixes only what follows the prefix. `pkit/fillers/` is the backbone's sub-path, the third literal above. Its `pkit/` segment marks the folder as the methodology's among the project's own documents, as the `pkit:` key does in front matter. Because the backbone owns the sub-path, no component places documents in it (COR-052 point 2).

| Address | Path, with the default internal root |
|---|---|
| `pkit::documentation:readers` | `docs/pkit/fillers/pkit/documentation/readers.yaml` |
| `pkit::analysis:revalidation-evidence` | `docs/pkit/fillers/pkit/analysis/revalidation-evidence.yaml` |
| `super-docs::documentation:readers` | `docs/pkit/fillers/super-docs/documentation/readers.yaml` |

The first `pkit` in each path is the fixed sub-path. The second is the role's publisher, and varies.

Two limits the grammar does not rule out:

- a word longer than a filesystem allows for one name, commonly 255 bytes, `.yaml` included for the point
- the device names Windows reserves (`con`, `nul`, `aux`, …)

Neither breaks injectivity, since each only makes a file impossible to create there. So a capability author avoids such words.

**The inverse.** Given a file under `<internal-root>/pkit/fillers/`: remove that prefix, require and remove the `.yaml` suffix, and split the rest on `/`.

- **Three parts:** exactly three parts, each a word, give the address `<first>::<second>:<third>`. The mapping sends that address back to the same path. So the two are inverse to each other on valid addresses.
- **Any other file:** any other file under the prefix is not a filler: two parts or four, a part that is not a word, `.yml` or no suffix. Such a file binds to no point, and is reported rather than skipped in silence.

This is the walk the location rule performs.

**What the file holds: the envelope.** The envelope is the backbone's (COR-052 point 2). Its schema is `.pkit/schemas/backbone/filler.schema.json`, which is the authority (the schemas reference's page on backbone files, "`filler.schema.json`"). The value inside it is the point's, judged by the companion schema of the point's active provider:

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
- **One key for both overrides.** COR-052 names a `union` point's *suppression* and an `additive` point's *removal override*. Both are the same act, to drop an id with a reason, so both are an entry of `remove`.
  - An entry of `remove` drops that id from every other filler, the capabilities' and the default's, before they merge. The project's own entries are its to write or leave out.
  - A `single` point has one answer and takes no removal.
  - A removal that matches no entry is reported as information.
- **Entries have ids.** A `union` or `additive` point's value is a list of entries. Each entry is a string, its own id, or a mapping carrying a string `id`, and no id comes twice in one filler. The point's companion schema describes the whole list. The ids are the backbone's requirement on top of it, since merging is by id.
- **Errors the project can fix.** Each of these is a validation error whatever the point's inert policy (COR-052 point 2), and such a file answers nothing:
  - a file that does not parse
  - a malformed envelope
  - a file targeting another version of the point
  - a value the point's schema refuses
  - a `remove` on a `single` point
- **Inert, not wrong.** A filler whose point no active provider defines has its envelope checked and its value left alone, and is reported as inert. A file under the prefix whose path names no point is warned.
- **The same envelope from a command.** A command filler prints this envelope as one JSON document, without `remove` ("How a data point resolves").
- **Editor support.** The authoring command that creates a filler file stamps the editor directive at the backbone schema's path. None ships yet. A directive written by hand is a YAML comment, not a key.

### How the wiring is resolved

The backbone has a **single wiring resolver** (COR-053 point 7), and `pkit validate` reports it. The graph, the status report and the install and uninstall plans (points 7 and 8) read its wiring, rather than computing wiring of their own. A plan resolves the installed set plus or minus a candidate through the same resolver.

The resolver reads only:

- package metadata, with the companion schemas its points name
- the configuration's `connections` block
- the installed versions
- the envelope version of each project filler file

The resolver runs no filler command and parses no process definition. What each data point resolves to is the layer over it ("How a data point resolves", below). It is deterministic: the same repository state yields the same wiring and the same findings, in the same order.

- **Provider selection.** One installed capability providing a qualified role is its active provider. Two or more need the `connections.providers` entry naming one.
  - Without that entry the role is in *conflict*, and no provider's points are defined. The conflict is an error located at that key, with the entry to add. The error also names, once per provider, the command that writes the entry (`pkit connections providers set <role> <capability>`, the CLI reference's "Connections commands").
  - An installed provider that is not the selected one keeps its commands, but its points are not defined and its own extensions are inert. It is warned.
  - A selection naming a capability that does not provide the role is the configuration pass's error (below).
- **Compatibility is an equal integer.** A contribution, subscription or `depends-on` entry binds to the active provider's point when its `schema_version` equals the point's. Otherwise the counterpart is **inert**, warned, and delivered nothing. A counterpart naming a point its role's active provider does not define is warned with the points it does define. A `depends-on` entry may omit the version, and then binds on existence alone:
  - in the role form, of an offered process point
  - in the implementation form `<capability>:<process-id>`, of an offered point with that `process` id, or of a definition file at `schemas/<process-id>.yaml`. This is existence only: a definition kept under another file name is not found this way.
- **Optional by default, mandatory with a reason.** A counterpart to a role nobody provides, or to an upstream whose capability is not installed, is silent unless marked mandatory.
  - A mark on an accepted point is unmet when nothing but the default fills it. A mark on a contribution or subscription is unmet when no compatible target exists. A mark on a `depends-on` entry is unmet when the upstream is missing or at another version.
  - An unmet mark is an error on the side carrying it, with the fix named: meet it, or drop the mark. The capability the mark targets, when there is one, is warned with the carrier named. This is COR-030's direction split, as COR-053 point 6 applies it.
  - Unmet marks are reported with the connections, whatever their cause.
- **Cycles.** Mandatory marks that face each other are rejected, with an error on each mark in the cycle: no member could be installed first. Marks face each other in every strongly connected group of capabilities joined by mandatory connections. An edge is drawn only to a role's *active* provider, since which provider is selected decides whether a cycle exists. An unselected provider's marks bind nothing.
- **Fingerprints.** Two installed providers of one qualified point and version must define the same companion schema. The fingerprint is the sha256 of the schema's canonical JSON, compared and kept nowhere. Key order and layout never count, and any other difference does. A disagreement is an error on each provider.
- **The contributor selection.** A `single` data point with contributions from more than one capability needs the `connections.selections` entry naming one. A point that declares no `combination` is a `single` one. Without that entry, there is an error at that key.

**Version relations.** Each relation is checked deterministically and reported by functionality. The resolver's relations are reported under a `versions` heading, which counts how many of each were checked. The heading labels each finding with its relation.

| Relation | Checked | Finding |
|---|---|---|
| Backbone range | each component's `requires_backbone` admits the installed backbone version | error on the component — `[backbone range]` |
| Capability dependency ranges | each `requires_capabilities` entry names an installed capability whose version of record the range admits. The version of record is its component manifest, else its package: the order the install gate reads. An optional entry whose capability is not installed passes | error on the dependent, warning on the dependency naming each dependent — `[capability dependency range]` (COR-030) |
| Contributions and subscriptions against point versions | the counterpart's `schema_version` equals the point's | warning: the counterpart is inert — `[point version]` |
| Process connections against interface versions | a `depends-on` entry's `schema_version`, where it declares one, equals the offered process point's | warning: the entry is inert — `[process interface version]` |
| Project filler files against schema versions | the filler envelope's `schema_version` equals the point's | error at the filler — `[project filler version]`. The file sits at the path "Where a project filler file lives" gives. One whose envelope carries no integer `schema_version` fills nothing, and its envelope error is reported under `connections` |
| Rule-set inheritance pins | each `inherits` pin of a rule-set file against the major of the set it names (COR-051 point 7). The pins are read from the rule-set files (the schemas README, "Rule-set files") | error on the inheriting rule set, naming the new major — `[rule-set pin]`. A pin naming no set, or one it may not inherit, is the `rule-sets` pass's finding |
| Configuration shape against the installed backbone | the configuration file carries no version key. The configuration pass validates it against the `config.schema.json` the installed backbone ships in the tree | reported under `configuration` |

A mandatory counterpart at another version is reported with the connections, as an unmet mark (above).

The configuration pass checks the two selection keys against the same declarations. A provider entry names a capability that provides the role. A contributor entry names a `single` data point some installed provider defines, and a capability that contributes to it.

**The graph and the status report read the same wiring.** `pkit connections graph` draws the wiring together with the process definitions' edges, and `pkit process graph` is that graph's process view. `pkit status` shows the wiring per role and per point, and the unmet marks it shows are the ones this resolver judges. `pkit connections providers set` writes the provider selection after the same check the configuration pass applies. The CLI reference's "Connections commands" and "status" specify them.

### How a data point resolves

The data kind of connection point resolves to a **value** ([COR-052](../decisions/core/COR-052-slots.md), COR-053 point 2). The value is:

- what the status report shows
- what a project filler overrides
- what contributions merge into

The backbone computes the value as the second layer over the wiring, once per run of `pkit validate`, whose `connections` member reports it. This layer reads the run's one wiring and the filler files the wiring read, and never resolves either again. `pkit status` shows the same resolution. For each data point an active provider defines:

**The fillers, in precedence order** (COR-052 points 2 and 4):

1. **the project filler** — the file at the path the point's address maps to ("Where a project filler file lives").
2. **each contribution** of an installed capability (`extensions.contributes`), in capability-name order: its `value`, or what its command filler prints. A contribution at another version than the point's is inert (the wiring warns it). A contribution whose capability provides a role for which it is not the selected provider is not delivered (COR-053 point 1).
3. **the definer's default** (`default.value`), as the point declares it takes part:
   - `always`: like any other filler, at the lowest precedence
   - `alone`: only when no other filler is declared. That means no project filler file, and no contribution to the point, in step or not, other than an unselected provider's. An `alone` default is **never promoted because a declared filler broke**.

**The policy** (`combination`, COR-052 point 3):

| Policy | The value | Collisions and overrides |
|---|---|---|
| `single` (also when none is declared) | the answer of the first filler in precedence order that answers. The others are not asked, and a command filler not asked is not run | among several contributions, the contributor selection (`connections.selections`) picks one. Several with none selected leave the point unresolved, the wiring's error at the selection key, unless the project filler answers, since it precedes them all. The default never stands in for a choice nobody made |
| `union` | a set: every answering filler's entries merged by id, listed by id. | a project entry replaces a capability's or the default's entry with that id **whole**, never field by field. A capability's entry replaces the default's. Two capabilities supplying one id is an error until the project settles it. An entry of the project's own with that id replaces both, or `remove` drops the id |
| `additive` | a list: every answering filler's entries, in precedence order — the project's, each capability's, the default's. | any id supplied twice is an error, the project's included: nothing overrides. An entry leaves only through a removal override, and the project may then supply its own under that id |

**Choosing entry ids.** A point's definer chooses an id that identifies what one filler alone can say. Where several fillers can each report on one subject, the id carries a part the filler names, opening with the filler's own name. Their entries then stand side by side, and only a real double claim collides. One filler never supplies an id twice, so that part is as fine as one entry.

`remove`, the project filler's removal overrides, drops each id from every other filler before they merge. Each removal carries its reason ("Where a project filler file lives"). A collision leaves the point unresolved: a gate never reads one of two entries picked by accident.

**Command fillers, and the parameter rule.** A contribution's `command` is a query (COR-052 point 6), under these rules:

- The command **takes no parameter**, since a data point is a value. So a question that needs an input, such as which documentation one change owes, is not a data point but a process point. A process point's predicates take the one subject. The need is met by either:
  - a parameterless point listing the obligations, which the gate applies to the change
  - a process point whose subject is the change
- The command runs under the query policy of the one runner ("How a registered command is run"). Its `commands:` leaf must declare `query-contract: true`: the `packages` member reports a leaf without it, and such a command is never started. Then, whichever command started the resolution, the command is run:
  - from the project root, with `--json` alone
  - with the offline marker set, and the base override (`PKIT_CHECK_BASE`) and the change's own head (`PKIT_CHECK_HEAD`) removed
  - in its own process group, bounded by thirty seconds. When the point is read inside another run, the bound is what remains of that run's bound. The process group is then the outermost run's ("A run inside a run").

  The command prints one filler envelope, `{"schema_version": <the point's version>, "value": <the point's value>}`.
- Each of these is **no answer**, never an empty and never a partial one, and the filler is inert:
  - an abnormal exit
  - a timeout
  - output that is not exactly that envelope
  - an answer at another version, or one carrying `remove`
  - a value that does not fit the point's schema whole
- Needing no network is declared and trusted, not enforced (COR-050 point 2). The status report shows, for each command filler, whether its command declares it.

**What a command filler reads** (COR-052 point 6). A filler reads state, and never a base named for one run:

- the working tree
- the current history
- of settled state, only the default branch, as the backbone resolves it ([COR-054](../decisions/core/COR-054-default-branch.md) point 2), whatever branch a change targets

A filler does not compare the branch at hand with settled state either.

- **The declaration.** Beyond the working tree, a filler's `commands:` leaf declares what it reads: `reads: [history]`, `[settled]` or both ("The methodology's literals"). With no `reads`, the filler reads the working tree only. What a filler reads is declared and trusted, as the query contract is:
  - the filler reads history and settled state through the backbone's reading commands, `pkit repository base --json` ([the CLI reference](../cli/README.md#repository-base---base-ref---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->). It reads that document's `head` for whether there is history, and its `default_branch` for the default branch, never its `base`.
  - the filler resolves no reference itself
  - the filler does not compare the branch at hand with settled state

  A `reads` this reading does not understand is the `packages` member's error, and the filler is not started.
- **What the backbone enforces.** No base override and no change's own head reach a filler, whichever command resolves the point: `pkit validate`, `pkit status` or `pkit connections resolve`. HEAD, whether the clone is shallow, and the default branch are read once per resolution, when a filler first declares `reads`.
  - A filler that declares `settled` is **not started** while the default branch resolves to no commit for any reason but having none yet:
    - a remote holds it and this clone has not fetched its copy
    - the declared name names no branch here

    Such a filler is inert, and its reason names the fetch (`git fetch origin <default-branch>`) and the declaration as the fixes, never a base. The point's inert policy decides the rest: an error under `fail`, a warning under `fallback`.
- **Empty is an answer, unreachable is none.** State that does not exist yet holds nothing, and the filler answers with an empty value. State that exists and cannot be reached from this clone gives no answer, never an empty one.
  - State that does not exist yet is one of these, and either starts the filler:
    - a repository with no commit: HEAD a branch before its first commit (`unborn` in the reading's `head`)
    - a default branch nothing has been committed to: no remote, and HEAD that branch before its first commit (`unborn` in its `default_branch`)
  - A commit git cannot read here is state that cannot be reached, never a repository with none.
  - Where a remote exists and this clone has no copy of its default branch, a branch never pushed looks the same as one not fetched. So the backbone treats both as unreachable and refuses. A filler that declares `settled` is inert there until the branch is first pushed or fetched.
  - Only the filler knows how much history it needs. So a history a shallow clone cut short of it is the filler's to detect, and the filler exits non-zero.
- **What the reports name.** For each command filler that declares `reads` and was asked, the reports name the state it declared and the commit it was read at. The filler's answer depends on what the clone has fetched (COR-052 point 7).
  - The `connections` member of `pkit validate` adds one line per such filler, taken or inert:
    - `<address>: <capability> (command '<ref>') reads history (HEAD <sha12>[, shallow clone])`
    - `… reads the default branch (<ref> at <sha12>)`
    - the two joined with `and` when it reads both
    - `(HEAD, no commit yet)` or `(<name>, no commit yet)` where there is none yet
    - `history (git cannot read HEAD here)` where HEAD names a commit git cannot read
    - `the default branch (it resolves to no commit here)` for a filler not started because the default branch cannot be read
  - The status report appends the same to the filler's line.
  - `pkit connections resolve --json` carries it as `fillers[].reads`.

**The inert policy** (`inert`, COR-052 point 6). A filler meant to answer that cannot is inert:

- its version differs
- its command gave no answer
- its value does not fit

The point's inert policy is one of these:

- `fallback` (also when none is declared): the point resolves from the fillers that remain, with a **warning** naming the inert one. If none remains, the point is unresolved, with the warning.
- `fail`: the **whole** point is unresolved, whatever its policy, with an **error** naming the inert filler. So a gate never passes on the entries that happened to survive.

**Which policy a point declares** (COR-052 point 6). `fail`, when anything refuses or fails on the point's value: a gate, a check, a finding that fails validation. A point whose every use is advisory may declare `fallback`.

A use is advisory when it only reports:

- nothing refuses on the point's value
- nothing fails on it
- no finding is drawn from an entry's absence unless the point resolved with no filler inert. What an inert filler would have supplied is unknown, not absent.

The point's definer chooses. Where one point serves both kinds of reader, the stricter use decides. The stricter use decides again when an advisory reader comes to refuse or to fail anything.

A defect of the project's own filler is an error whatever the policy (above), and that filler answers nothing. Its error is the one finding, and the point follows its inert policy for what remains.

**What `pkit validate` reports, under `connections`.** In this order:

- a count line: data points defined, resolved and unresolved, and project filler files
- a line per command filler that reads beyond the working tree ("What a command filler reads")
- the findings:

| Severity | Finding |
|---|---|
| error | a project filler that does not parse, a malformed envelope, a value its point's schema refuses, or a `remove` on a `single` point. The envelope at another version is the `versions` member's `[project filler version]`. Two capabilities supplying one id to a `union` point, and any collision in an `additive` point. An inert filler of a `fail` point |
| warning | an inert capability filler or default of a `fallback` point. An out-of-step contribution is the `versions` member's warning, not repeated. A file under the fillers prefix that names no point. A point whose companion schema cannot be applied, which does not resolve |
| info | a removal override that matches no entry of the other fillers |
| report | a project filler whose point no active provider defines: inert, its envelope checked, its value not read |

Each of these is the `packages` member's error:

- a filler command lacking the declaration
- a `reads` on a leaf without it
- a contribution naming both `command` and `value`

**What `pkit status` shows** (COR-052 point 7), under "Data points":

- where the project's filler files live, and how many there are
- how many points are defined, resolved and unresolved
- then per point:
  - its policy, inert policy and default participation, and whether it resolved or why not
  - its value, which is one of these:
    - a `single` point's answer, with the filler that gave it
    - each entry of a `union` or `additive` point, with its origin and what it replaced
  - each removal override, with its reason and the fillers it removed from
  - every filler considered, `taken`, `inert` or `passed over`, with the reason. A command filler says whether its command declares the query contract. Once asked, it also says what it read beyond the working tree, and at which commit.

**Reading one point from a script.** `pkit connections resolve <address> --json` prints the same resolution of one point as a stable document ([the CLI README, "Connections commands"](../cli/README.md#connections-resolve-address---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->). It is how a component's own script reads a point it defines, before applying the value itself. A capability script runs in its own environment and does not import the backbone. The consumer, not the point, knows what the value is applied to.

- **A consumer dispatches on `outcome`, never on `why`.** `outcome` says how the resolution ended, as one value from a closed set: `resolved`, `unfilled`, `collision` and the rest the CLI README lists. `why` is that ending's sentence for people, and its wording is no contract. The filler states alone cannot tell the endings apart: a collision looks like a point nothing fills.
  - A consumer that turns a rule off when nothing fills the point reads `unfilled`, not the absence of a taken filler.
  - A value it does not know means it could not tell how the point ended: never `resolved`, never `unfilled`.
- **`resolved` does not say every filler answered.** A point that resolved with an inert filler among several is `resolved` too. So a consumer that only reports checks that no `fillers[].state` is `inert` before it draws a finding from an entry's absence. What an inert filler would have supplied is unknown, not absent (COR-052 point 6).
- **The command resolves that point alone.** Only its fillers are asked, so no other point's command filler starts. Reading one point costs what that point costs, however many others the project has. `pkit validate` and `pkit status` still resolve every point.
  - Within one run, each point resolves at most once, whichever reader asks first, sharing the run's one wiring and filler files.
  - Points never read one another, so a point resolved alone is the point resolved among all.
- **A run of `pkit validate` spans processes.** A capability's validator reads a point through this command, so the run keeps what it resolved in a **run cache**. The cache is a fresh temporary directory, named in the environment of every command the run starts (**`PKIT_RUN_CACHE`**). The directory is removed when the run ends. When no directory can be made, the run goes without one, and every reader resolves for itself.
  - **Who uses the cache:** only a process of the run, the one that opened it or one running inside a live run ("A run inside a run"). So a variable left over in a shell is ignored, and a `pkit validate` started there opens a fresh one.
  - **What an entry holds:** each point resolved in the run is written there with the findings its resolution made and the bound it was resolved under. An entry records the resolution its first asker made, within the time that asker had.
  - **What is not written:** a resolution in which a command filler gave no answer for want of the time its asker had. The filler overran the time its caller had left, or had none left to start in. A reader with more time might get an answer, so the next reader resolves the point itself.
  - **A point already there:** `pkit connections resolve`, inside the run, prints the point from the cache without resolving anything, not even the wiring. It says so in its document's `from` (the CLI README, "Connections commands"). Otherwise it resolves the point, writes it there, and its `from` says so.
  - **Once per validate:** whichever process of the run asks first resolves a point. So its command fillers run once per validate, however many validators read it. They run again only after an asker ran short of time.

### A data point's question

A data point's definer may need an answer only the person can give about the point, such as whether to grant what a contribution offers. The definer names a command of its own that asks and records, `question` on the point ([COR-061](../decisions/core/COR-061-point-questions.md) and "Field layout and casing" above). The backbone runs it.

- **When.** At the end of three operations, once each has made its own writes:
  - `pkit capabilities install` and `register`
  - `pkit capabilities upgrade`, whatever the capability's origin
  - `pkit upgrade`, after the completion and the pin ([`upgrade-flow.md`, "The steps of a transition"](upgrade-flow.md#the-steps-of-a-transition) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->)

  `pkit sync` never runs one. Nor does `pkit upgrade` when the project is already current, since no transition runs.
- **Which.** Read from the wiring the operation leaves ("How the wiring is resolved"):
  - for a capability's install, register or upgrade: the question of each point it defines, and of each point its contributions reach, bound or not
  - for `pkit upgrade`, every question
  - only a point an active provider defines, each question once, in the order of the points' addresses
- **Where a person can answer,** with standard input and standard output both terminals, each question runs in turn. The leaf's script is started through the dispatcher's proxy run ("How a registered command is run"). The script runs from the project root, with no argument, the terminal's streams and no time bound. Before each, the backbone prints `asking <address>: pkit <definer> <command>`.
- **With nobody to answer,** none runs and nothing is recorded. The backbone prints one `not asked <address>: pkit <definer> <command>` line for each, the command to run at a terminal later. The backbone cannot tell whether anything waits for an answer, so the command may then have nothing to ask.
- **A preview,** under `--dry-run`, prints `would ask <address>: pkit <definer> <command>` for each question of the wiring the operation would leave, with the versions it would bring, and runs none.
- **A question that fails** prints a `warning` line naming how it ended and the command to run again, and the next question still runs. It leaves the operation's exit status as it was. A question whose command names no script is reported and not run.
- **An interrupt** reaches the question's command, which may save what it was told before it ends. The backbone only notes it while the command runs, as a shell does, and then stops the questions: each one left gets its `not asked` line.
- **Neither undoes the operation,** which was complete before the first question ran.

**What the command does is the definer's.** The command reads what it needs, such as the point's value through `pkit connections resolve`. It asks only what has no recorded answer, and asks nothing where nothing waits. It records each answer the person gives in the definer's own state, and never one the person did not give. Its words and its record are the definer's, and its own documentation says what it asks.

**Readable before it runs.** `pkit capabilities show` lists a point's question beside its policy, from the package metadata alone ("Discovery: what a capability would connect to", below).

### Discovery: what a capability would connect to

A capability's connections are readable without installing it. What an install or an uninstall would change in the wiring is known before it happens ([COR-053](../decisions/core/COR-053-connection-points.md) point 8). The backbone computes all of it from the one resolver ("How the wiring is resolved"), and resolves nothing of its own. The commands are in the CLI reference, "Discovery".

**The local catalogue.** Where a capability not yet installed is found:

- the capabilities registered in the project, read from their installed tree
- capability subtrees authored in the repository at `.pkit/capabilities/<name>/` and not registered (incubated, COR-031)
- the capabilities that ship with the running pkit: its kit source, the tree installed with the tool

A name in more than one place is read from the first, in that order. Where the repository's `.pkit/` *is* the kit source, an unregistered capability there is kit-shipped. All three are on disk: nothing is fetched to read a capability, to plan for it or to suggest it.

**`show`.** `show` reads the package metadata alone, `connections.roles`, `extension-points` and `extensions`, as the resolver reads them, with the same parser, descriptions included. It also gives what would connect here. For an installed capability, that is the live wiring's bindings to and from it. For one not installed, it is the bindings of the wiring the resolver computes with it added.

What else `show` lists beside its connections is in [the CLI reference's section on it](../cli/README.md#discovery-show-the-plans-and-suggestions) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->.

**A plan is exact because it runs the resolver.** A plan runs the live resolution over the installed set plus or minus one capability. Everything else is read from the tree as the live wiring reads it: the selections, the installed backbone version, the project's filler files.

- A candidate is read where it is, its companion schemas and its definitions. It is located where the operation will put it (`.pkit/capabilities/<name>/package.yaml`), with the version its package declares: the version install stamps and register reads. It comes after the installed components, where install appends it to the registry.
- The plan is the difference between the live wiring and that one, in terms that do not depend on where anything was read:
  - the roles whose answer changes
  - the points defined and no longer defined
  - each counterpart whose status or answering capability changes
  - the findings added and resolved, located relative to the project root
- The wiring the operation then leaves differs from the one before it by exactly that difference.

| Plan | Lists |
|---|---|
| Install (`install --plan`) | the connections it would make, and those it would break. Each role conflict it would open, with the provider-selection command that resolves it, one per provider (`pkit connections providers set <role> <capability>`). What the capability needs: the errors the install would put on the capability's own package. Each is an unmet mandatory mark, a mandatory cycle, or a backbone or capability range the project does not meet. Each type it would bring whose name a bare project type uses, with the project places giving that type. The project renames that type before the install, or its validation fails (COR-056 point 2). The role blocks whose meaning changes (COR-053 point 10, "Keys"). One kind is an orphaned block the new provider adopts. Another is a bare key a second active role would make ambiguous. Rewriting it is the project's, with consent |
| Uninstall (`uninstall --plan`) | the fillers lost. They are its contributions, with whether each point stays filled, is left unfilled or is no longer defined. They are also the project filler files answering a point it defines that no provider would define after it, kept and inert. The processes left without a provider (`depends-on` entries it answered), and every other counterpart left without one. The artefacts whose role blocks would be orphaned, preserved and reported, never an error. The selections in the configuration left naming it |

Both then list the roles, points and findings that change. A plan writes nothing and runs no filler command, since the resolver resolves wiring, not data (COR-053 point 7). What a plan does not predict, stated:

- The role blocks a plan judges are those of the artefacts in the places declared now. So a place the operation adds or removes is not walked in advance.
- Rule-set pins are relations between rule-set files, not connections, and are left out of the difference.

**Suggestions — a suggestion is never an action.** Where the live wiring has an unmet need, the status report names each capability of the local catalogue not installed whose package would answer it:

- a data point filled by nothing but its default, answered by a contribution at the point's version
- a role an installed counterpart targets and no installed capability provides, answered by the role among its roles
- an implementation-addressed upstream not installed, answered by the upstream by name

Suggestions are read from package metadata on disk only, and never fetched. A suggestion is text: the capability, why, and `pkit capabilities show <name>`. Nothing is installed, selected or written. Suggestions have one computation, which any view of the wiring reads rather than suggesting on its own.

## Worked example

For concrete examples of the contract the lifecycle reference defines, see these files, where the project has them:

- The project's own backbone manifest, for its shape with adapter and capability entries.
- `.pkit/migrations/backbone/<X.Y.0>/`, for backbone migration script structure.
- `.pkit/capabilities/project-management/migrations/0.12.0/`, for a capability-tier migration that handles file-rename + adopter-state cleanup.
- `.pkit/adapters/<adapter>/migrations/`, in the methodology's source, for adapter-tier migration patterns. A project's copy of an adapter carries none ("An adapter's manifest", above).

A full worked example of the upgrade flow across the backbone and its components is deferred.
