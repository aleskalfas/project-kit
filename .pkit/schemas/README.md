---
variant: specialized
---

# Schemas

> A **schema** is a structured data file plus a companion shape declaration. The kit defines the convention; capabilities, adopter projects, and future kit features adopt it.

The schemas mechanism gives the kit a uniform way to encode machine-consumable rules and data — state machines, enumerations, regexes, mapping tables, structured records, cross-referenced datasets — separately from the code that consumes them. Engine code stays methodology-agnostic; methodology (or domain data) becomes editable without touching code.

This area is the **mechanism reference**. It defines what schemas are, how they're shaped, how they cross-reference each other, and what tooling expects from them. Decisions that *adopt* the schemas mechanism for a particular context (capability engine data, adopter project data, future kit features) live as their own records and reference this area.

## When to reach for schemas

Use a schema when a methodology has *quantitative or structural* content that some piece of code needs to consume mechanically — enumerations of allowed values, regexes for shape checks, transition graphs, field lists, ordered taxonomies, lists of records. The schema is the single source of truth; consumers read it at runtime.

Don't use a schema for purely qualitative content — principles, rationale, when-to-apply judgement. That belongs in prose (decisions, READMEs). The schema's *value* is machine-consumability; if no code consumes it, it's just data noise.

## The schema is a pair

A schema is two files paired one-to-one:

| File | Carries | Audience |
|---|---|---|
| `<name>.yaml` | Instance data — the actual rules, enums, records | Engine code reading the data at runtime; humans editing the data |
| `<name>.schema.json` | Formal shape declaration — what the YAML must look like | JSON Schema validators (CI gates, IDEs); humans verifying the shape |

Neither half alone is the schema. The YAML carries the facts; the companion declares what counts as valid facts. Together they enable autocomplete in editors, machine validation in CI, and a stable contract for anyone authoring or consuming the data.

## YAML conventions

Every schema YAML follows the same envelope:

```yaml
schema_version: 1   # required, first key
source:             # optional — only when the schema distills from an external spec
  upstream: <project-name>
  commit: <40-char SHA>
  decisions: [<external-decision-id>, ...]
  captured_at: YYYY-MM-DD
# …domain-specific fields…
```

Rules:

- **`schema_version: <int>` is the first key**, always. The integer is the schema's own version; consuming code switches on it when the shape evolves.
- **`source:` is an optional structured block** carrying lineage to an external spec when applicable (e.g., a methodology being distilled from an upstream repo). Omit when the schema is its own source of truth.
- **Field names use `snake_case`**, matching the kit's other YAML conventions (`schema_version`, `requires_backbone`, `backend_state`).
- **Identifier values use `kebab-case`**, matching kit-wide slug conventions (`github-sub-issues`, `claude-code`).
- **Multi-line prose uses block scalars** (`|`), matching the evidence-record convention.
- **Leading comments document the schema's purpose and source** in plain prose; inline comments only where a field's purpose isn't obvious from its name.

## JSON Schema companion convention

Every YAML schema ships a companion JSON Schema declaring its formal shape:

- **File naming.** The companion is `<schema-name>.schema.json` in the same directory as the YAML. For `<root>/issue-types.yaml` the companion is `<root>/issue-types.schema.json`. Side-by-side; no sub-directory split.
- **JSON Schema draft: `2020-12`.** Every companion declares it via the top-level `$schema` keyword:
  ```json
  { "$schema": "https://json-schema.org/draft/2020-12/schema", ... }
  ```
- **Validates the envelope.** The companion's `properties` block constrains `schema_version` (typically `"const": <integer>`), declares `source` as an optional object when applicable, and validates each domain-specific field's type and value constraints.
- **Companion is required, not optional.** A YAML schema without a companion is incomplete. Consumers and tools can rely on the companion always existing.

### Which YAML the companion requirement covers

The companion requirement scopes to **schema definitions**, not to every YAML that happens to live under a `schemas/` tree. A schema definition is a **direct `schemas/<name>.yaml`** paired one-to-one with a side-by-side `<name>.schema.json`; the validator (`pkit schemas validate`, and the same walk register's self-consistency check reuses) enumerates only those and flags a genuine schema YAML that ships no companion. Two categories of *non-schema* YAML are excluded, so they need no companion of their own:

- **Fixtures and examples.** YAML under any `examples/` directory, or named `*-example.yaml`, is an instance/fixture demonstrating a schema — categorically not a schema itself.
- **Instances of an external/shared schema.** YAML that declares a `$schema` pointer — a `# yaml-language-server: $schema=<path>` directive comment (per COR-023's IDE binding) or a top-level `$schema:` key — at a schema **other than its own `<name>.schema.json`** is an *instance* validated against that named schema, not a definition. A common shape: process-definition YAMLs validated against one shared `_defs/<name>.schema.json`. (A `$schema` pointer at the YAML's *own* companion is an ordinary pair — the companion is still required.)

Subdirectories under `schemas/` hold material that is not a pair: `_defs/` the shared `$defs` library and pointer targets, `backbone/` the backbone file schemas (below), `examples/` samples. The companion requirement lives with the direct-child schema definitions.

### The pointer is validated, not just classifying

An instance is exempt from the **companion** requirement, not from validation. `pkit schemas validate` — both the project-wide walk and a path-scoped run — validates every pointered instance against the schema its pointer names, so the pointer means what it says: a hand-edited definition that violates the shape it claims to conform to is reported. Details:

- **The pointer resolves relative to the YAML's own directory**, which is the form the IDE reads and the form authoring commands stamp (e.g. `../../../schemas/_defs/process.schema.json` from a capability's `schemas/` directory).
- **Findings report against the instance's path** plus a JSON pointer into the offending position (`demo.yaml/process/subject/cardinality`) — the instance is what the author edits.
- **A broken pointer is a finding, not a skip.** A target that is missing, unreadable, not JSON, or not a valid Draft 2020-12 schema is reported against the instance: declaring a contract and mistyping its path would otherwise leave a file unchecked with no signal.
- **The target needs a root.** A JSON Schema whose body is only `$defs` accepts every document, so a shared fragment intended as a pointer target declares root constraints (`type` / `required` / `properties`) alongside its `$defs`. Companions that cross-file `$ref` `#/$defs/*` are unaffected by those root keywords.
- **Shape only.** The cross-file reference passes (typed tokens, `x-pkit-keys-from-namespace`) are companion-pair concepts — sibling-file scope, keyed on the YAML's stem as its namespace — and an instance has neither. Instance-side references are `pkit data validate`'s surface (see COR-029 below).
- **A remote pointer (`https://…`) stays exempt and unvalidated** — it cannot be read offline. Kit-side spec points at local, repo-relative paths.
- **With the top-level `$schema:` key form the pointer is data**, so the target schema must permit the property — the same rule that has the kit's own companions declare `pkit_schema:`. The directive-comment form carries no such constraint.

The combination of YAML + companion JSON Schema means a schemas-aware editor (VSCode's YAML extension, JetBrains, etc.) gives autocomplete and inline validation on every YAML schema with zero per-file configuration. CI validators, language-level libraries (`jsonschema` in Python, `ajv` in JavaScript, etc.) all consume the companion the same way.

## Common shape patterns

A handful of structural shapes recur across schemas. JSON Schema expresses each cleanly; reuse the idiom rather than reinventing per schema.

### Envelope (every schema)

`schema_version` + optional `source` + domain fields. Defined once as a `$defs` fragment and referenced from every companion via `$ref` so all schemas share one envelope shape.

### Entry collections with stable ids

Many schemas hold a list of structured entries where each entry carries an `id` field used both for human reference and as a target for cross-schema references. The companion validates:

- Each entry conforms to a per-entry sub-shape.
- `id` is required.
- `id` values are unique across the collection.

The *shape* "list of objects with required `id`" is identical across schemas; the *collection name* (`transitions`, `records`, `types`, `entries`) is domain-specific. The reusable shape lives in `$defs` parameterised on the per-entry sub-shape.

### References between schemas

A field whose value names an entry defined in **another** schema — a workflow state declaring which issue types it applies to, a validation rule declaring its severity class, an aggregator pointing at entries in sibling files — uses the namespace-bearing token form:

```yaml
applies_to: ["[issue-types:task]", "[issue-types:feature]"]
severity: "[validation-severity:hard-reject]"
```

The token shape is `[<namespace>:<id>]`:

- `<namespace>` is the target schema's stem (filename without `.yaml` and without `.schema.json`).
- `<id>` is the target entry's id within that schema's collection.

Intra-schema references — a field naming an entry defined in the **same file** (e.g., a transition's `from` pointing at a state defined elsewhere in the same workflow schema) — stay bare:

```yaml
transitions:
  - id: open-to-review
    from: open       # bare — same file
    to: review
```

**Mapping keys stay bare, always** — whether they declare their own namespace or reference a foreign one. Definition sites should read cleanly:

```yaml
issues:
  epic:           # bare — not "[issue-types:epic]"
    required_sections: [...]
  feature:
    required_sections: [...]
```

When a mapping's keys reference a foreign namespace, the source namespace lives on the **JSON Schema companion**, not on each key. The parent field carries an `x-pkit-keys-from-namespace: "<namespace>"` annotation:

```json
"issues": {
  "type": "object",
  "x-pkit-keys-from-namespace": "issue-types",
  "patternProperties": {
    "^[a-z][a-z0-9-]*$": { "$ref": "#/$defs/issue_body_shape" }
  }
}
```

The resolver walks every field tagged with this annotation, iterates the mapping's keys, and confirms each key exists in the named namespace. Same cross-file validation as typed-token values; cleaner authoring at the definition site.

The split — typed tokens in values, bare ids + annotation in keys — reflects that key-position has a natural schema-side place to declare the namespace, while value-position doesn't.

(See COR-019 for the rule and rationale.)

### Validating the token shape

The JSON Schema companion validates a token's *shape* via a `pattern` constraint. The general form, defined once as a `$defs` fragment:

```json
{
  "$defs": {
    "reference_token": {
      "type": "string",
      "pattern": "^\\[[a-z][a-z0-9-]*:[a-z][a-z0-9-]*\\]$"
    }
  }
}
```

When a field accepts only one target namespace, narrow the pattern's namespace half:

```json
{
  "$defs": {
    "issue_type_ref": {
      "type": "string",
      "pattern": "^\\[issue-types:[a-z][a-z0-9-]*\\]$"
    }
  }
}
```

The narrowed form catches namespace typos at shape-validation time without waiting for the cross-file resolver. Both forms `$ref` from the field constraint via `#/$defs/<name>`.

JSON Schema does not look across files. Confirming that the token's target id **actually exists** in the named namespace is the consuming code's or a dedicated cross-file validator's responsibility. The kit ships that resolver as `pkit schemas validate`'s default pass; see below.

### Declaring where ids live: `x-pkit-id-collection`

To resolve a token like `[issue-types:task]`, the cross-file validator needs to know *where in `issue-types.yaml`* the ids live. Every schema that owns a namespace declares this via a top-level JSON Schema annotation:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "issue-types.schema.json",
  "title": "Issue type taxonomy",
  "x-pkit-id-collection": "/types",
  "type": "object",
  ...
}
```

The value is a **JSON Pointer** (RFC 6901) into the data YAML — `/types` points at the top-level `types` mapping; `/items` points at a top-level `items` list; nested pointers like `/groups/0/entries` work too.

The resolver supports two collection shapes:

- **Mapping** — keys are the ids (`types: { task: {...}, feature: {...} }` → ids are `task`, `feature`). This is the dominant shape across the kit's current schemas.
- **List of objects with `id` field** — each list item carries an `id` field whose value is the id (`items: [{ id: alpha, ... }, { id: beta, ... }]` → ids are `alpha`, `beta`). Use this shape when the collection's entries need a stable ordering or when other per-entry metadata makes the mapping form awkward.

A schema that doesn't own a namespace (an aggregator pointing at others' ids; a config-style schema with no entries of its own) omits the annotation. Tokens pointing *at* a schema without the annotation surface as resolver errors.

### What the resolver pass checks

`pkit schemas validate` runs two passes by default:

1. **Shape** — JSON Schema validates the YAML's structure.
2. **References** — two complementary walks:
   - **Value-position tokens.** For every value-position string matching `[<namespace>:<id>]`, the resolver looks up the target namespace's companion in the same directory, reads its `x-pkit-id-collection` pointer, walks to that collection in the data YAML, and confirms the id is present.
   - **Annotated key positions.** For every JSON Schema field carrying `x-pkit-keys-from-namespace: "<namespace>"`, the resolver walks to that data field, iterates its mapping keys, and confirms each key exists in the named namespace's id collection.

Resolver errors surface as hard-rejects (validator exits non-zero). Authors mid-refactor can opt out via `--shape-only`. Cross-directory resolution is not supported in v1 — sibling-file scope only.

### Aggregator schemas

A schema that collects references to entries spread across sibling files declares one referencing field per aggregated namespace. Each field's `$defs` constraint narrows to its target namespace:

```json
{
  "properties": {
    "transport": {
      "type": "array",
      "items": { "$ref": "#/$defs/transport_ref" }
    },
    "lodging": {
      "type": "array",
      "items": { "$ref": "#/$defs/lodging_ref" }
    }
  },
  "$defs": {
    "transport_ref": { "type": "string", "pattern": "^\\[transport:[a-z][a-z0-9-]*\\]$" },
    "lodging_ref":   { "type": "string", "pattern": "^\\[lodging:[a-z][a-z0-9-]*\\]$" }
  }
}
```

The aggregator schema carries no entries of its own — it points at them. This lets a root data file act as a single point of contact for a domain (a trip spec aggregating transport / lodging / activities; a project spec aggregating phases / deliverables / risks) without becoming unscannable. Detail moves to sibling files; the root references it.

### Reusable fragments via `$defs`

When the same sub-shape appears in multiple schemas — the envelope, entry-id constraint, token pattern, semver-shaped strings — define it once and `$ref` from each consumer. Drift reduces; one fix updates every dependent schema.

The kit settles two ownership rules for where the canonical definition lives:

- **Kit-wide patterns** (recur across capabilities — the generic `reference_token`, the structured `source` envelope) live in `.pkit/schemas/_defs/refs.schema.json`. Consumers `$ref` `refs.schema.json#/$defs/<name>`.

- **Namespace-narrowed patterns** (a typed token narrowed to one namespace — e.g., `issue_type_ref` for the issue-types namespace) live in the **namespace owner's own companion** as a published `$defs` entry. Consumers cross-file `$ref` the owner: `issue-types.schema.json#/$defs/issue_type_ref`. The owner is the source of truth for its own narrowed reference pattern.

Both forms use JSON Schema's standard cross-file `$ref`. The kit's `pkit schemas validate` builds a Registry covering every companion in the same directory plus the kit-wide `_defs/` library, so all relative `$id`-keyed `$ref`s resolve.

## Adopter data → schema binding (COR-023)

A schema is consumed two ways: by the engine of the capability that ships it (reading its own canonical YAML at runtime) and by *adopter-side data files* that follow the schema (e.g., `trips/<slug>/trip.yaml` follows `trip-planning:trip`). The first form's binding is implicit — the file lives at `<capability>/schemas/<schema>.yaml` and the engine knows what to read. The second form needs a declarative binding so the resolver, the IDE, and `pkit data validate` can answer "which schema applies to this file?"

Per COR-023 (superseding COR-022), the binding mechanism is two-layered:

### 1. The `pkit_schema:` field (recommended, authoritative)

An adopter data YAML carries a top-level `pkit_schema:` field whose value is the bare two-part form `<capability>:<schema-name>`:

```yaml
# yaml-language-server: $schema=.pkit/capabilities/trip-planning/schemas/trip.schema.json
pkit_schema: trip-planning:trip
schema_version: 1
slug: japan-2026
title: Japan (Tokyo)
# …
```

- The field's value is the bare reference (no brackets). Brackets in COR-019 delimit references *embedded in prose or other values* — needed when the surrounding context is text. In field position where the entire value is the reference, the brackets add noise.
- The field is optional but recommended. When present, it is authoritative — the resolver uses the field directly without consulting capability fallbacks.
- The YAML Language Server directive comment (`# yaml-language-server: $schema=...`) is the IDE-side counterpart: editors with no `pkit` integration still light up with autocomplete + inline validation. Two sources of truth, each serving a different tool surface; drift is bounded because the authoring step writes both atomically.

### 2. Per-schema `binds_to:` fallback

A capability schema declares path-pattern fallbacks via a top-level `binds_to:` field on the schema's YAML — a list of repo-relative globs the schema validates:

```yaml
# .pkit/capabilities/trip-planning/schemas/trip.yaml
schema_version: 1
binds_to:
  - "trips/*/trip.yaml"
# … rest is the schema's namespace content
```

- The field lives **on the schema itself**, not in a separate bindings registry. One source of truth per schema; bindings die with the schema when it's removed; no cross-file registry to keep in sync.
- The pattern is a glob (Python's `fnmatch` semantics) matched against the adopter file's repo-relative path. Note `fnmatch`'s `*` **crosses `/`** — it is not shell-style per-segment matching — and `**/<name>` is the shipped idiom for "anywhere in the tree".
- **Pick a glob narrow enough that nothing else in an installed tree matches it.** A *distinctive* filename (`workstreams.yaml`, `substrate-map.yaml`) is specific on its own, so `**/<name>.yaml` suffices. A *generic* filename (`config.yaml`, `settings.yaml`) is not: narrow it with the distinguishing path segments (e.g. `**/<capability>/project/config.yaml`), or rely on the adopter-side `pkit_schema:` field. The failure this prevents is asymmetric — a collision *across capabilities* surfaces as an ambiguous-binding refusal, but a collision with a **non-capability** file does not: it silently resolves to the wrong schema and reports a bogus validation failure on a correct file.
- The field is optional. Most schemas in the kit are namespace owners or capability-internal — `binds_to:` matters only for schemas that describe adopter-data files.
- When an adopter file omits `pkit_schema:`, the resolver walks every installed capability's `schemas/*.yaml`, collects `binds_to:` patterns, and uses the first matching glob. Multiple matches across capabilities surface as ambiguous (the adopter resolves it by adding the explicit field).

### Resolution order

For a given adopter data file:

1. **Field-first.** If the file carries `pkit_schema: <capability>:<schema>`, resolve it. The field is authoritative.
2. **Capability fallback.** Otherwise, walk installed capabilities (in backbone-manifest order); for each capability's `schemas/*.yaml`, match the file's repo-relative path against each schema's `binds_to:` glob entries.
3. **Refuse.** No field, no matching binding → the resolver reports a structured "no schema binding" error pointing the adopter at the two ways to declare one.

### Schema-version cross-check

The data file's `schema_version` field declares which schema version the data was authored against. The schema (the capability's `<schema>.yaml`) declares its current `schema_version`. When the two disagree, validation refuses with a structured migration hint naming both versions and pointing at the capability's migration tier. Auto-migration is out of scope in v1 — adopter data is often hand-edited, and silent transformation is the wrong default.

### `pkit data validate <path>`

The CLI surface for the binding mechanism. Resolves the binding for one adopter data file (or every YAML in a directory, recursively), runs JSON Schema validation against the resolved schema, and reports findings. Exits non-zero on any unresolved binding or validation failure.

This command is **distinct from `pkit schemas validate`** — the latter validates the schema pairs in both homes — the core area (`.pkit/schemas/`) and every installed capability's `schemas/` (the spec); the former validates adopter-side data files against those schemas. Two artefacts, two surfaces.

### Cross-file references in adopter data: `x-pkit-reference-namespace` (COR-029)

Adopter data files reference each other: a `[<namespace>:<id>]` token in one bound file names an entry defined in another bound file (e.g. a trip's aggregator file citing `[transport:asiana-fux5mv]`, defined in that trip's transport file). `pkit data validate` resolves these in a second pass after shape validation (default-on; `--shape-only` skips it).

Two things make adopter-data references different from the capability-side resolution `pkit schemas validate` runs:

- **Resolution is *through the binding*, to the bound instance.** A capability schema that *describes* adopter data keeps its own id collection empty by design — the entries live in the adopter tree. So a reference does not resolve into the namespace schema's own (empty) collection; it resolves into the files *bound* to that namespace, read via the schema companion's `x-pkit-id-collection` pointer.
- **References are *position-gated*.** Adopter data carries bracketed tokens that are not references (prose, free-text). The resolver inspects **only** fields the citing schema's companion marks with `x-pkit-reference-namespace: "<namespace>"` — the value-position counterpart to the key-position `x-pkit-keys-from-namespace`. The annotation declares "this position holds references in this namespace"; the namespace is still carried by the token itself. Mark a scalar field, an array's `items`, or a shared `$defs` definition that other fields `$ref`:

  ```json
  "$defs": {
    "transport_ref": {
      "type": "string",
      "x-pkit-reference-namespace": "transport"
    }
  }
  ```

**Scope is the validated subtree.** A namespace's id pool is the union of every in-scope file bound to it — where "in scope" means under the directory `pkit data validate` was pointed at. Isolation is by *what you validate*: validate one instance's subtree and only its data is in scope; validate a parent and a shared file under it serves every instance below. Resolution is not positional (moving a file within the scope changes nothing) and there is no shadowing (the pool is a union).

**Failure surface:** a dangling id (the namespace has a pool in scope, the id is absent) is an **error**; a **duplicate** id across in-scope files of one namespace is an **error** (the pool is ambiguous); a reference whose namespace has **no bound file anywhere in scope** is a **warning** — incremental authoring routinely references a not-yet-created sibling, so this does not fail the run.

Deferred to successor decisions (each pending a real consumer, per COR-029): cross-scope shared reference roots (a shared catalog serving instances without unioning them into one scope) and foreign-keyed mapping keys.

### Authoring

The `schema` skill (composite per COR-020) covers adopter-data schemas through its `author.md` and `extend.md` sub-procedures. A pair is stamped into its owner's home by `pkit new schema <owner> <name>` — `<owner>` is a capability name, or `core` to stamp into this area (`.pkit/schemas/`), which the sibling verbs (`schemas validate` / `list` / `show` / `add` / `rename`) treat as an owner alongside every capability. Stamping a schema that describes adopter-data files includes adding the `binds_to:` field to that schema's YAML alongside the namespace content; adopter files themselves carry `pkit_schema:` + the IDE directive as recommended.

## Backbone file schemas and the methodology's front-matter container

Most schemas here govern **kit-shipped YAML** — a capability's own data file with its companion, or an instance that points at a shared shape contract. A second class governs **files the backbone does not author but validates**: the backbone configuration file ([COR-048](../decisions/core/COR-048-backbone-configuration.md)), rule-set files ([COR-051](../decisions/core/COR-051-rule-sets.md)), the project filler files that answer a data point ([COR-052](../decisions/core/COR-052-slots.md) point 2), and the methodology-owned block inside an artefact's front matter ([COR-053](../decisions/core/COR-053-connection-points.md) point 10). These are the **backbone file schemas**. Three things hold for all of them, each decided by the record named:

- **They live in the tree**, under `backbone/` in this area, as companion-only JSON Schema files: schemas are propagated data, and the configuration file's shape is the one the *installed* backbone defines, which is the tree (COR-048 point 6). The binary reads the same files and carries no second copy.
- **They bind by location, never by a field in the file.** The configuration file by its fixed path (COR-048 point 1); a filler file by the path derived from its point address under the internal documentation root (COR-052 point 2; the mapping and its inverse: [the lifecycle README, "Where a project filler file lives"](../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping)); a rule-set file by the places declared to hold rule sets (COR-051 point 2); the container in the front matter of a Markdown document, or in a collection entry, in a declared place (COR-050 point 1). Location rules will be consulted before the capability-data resolution below; a file they claim never reaches `pkit_schema:` / `binds_to:` resolution, and a plain YAML data file in a declared place is not a document and falls through to it.
- **Strict at validation.** An unknown key is an error carrying the nearest known key (COR-048 point 4 for the configuration file; each owning record for the rest). A version is written only where a *capability* owns the shape — the filler envelope and a role block's point blocks carry the point's `schema_version` (COR-052 point 5) — while backbone-owned shapes carry none and are migrated when they change ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)).

`pkit validate` will run them (its registered-validator pass is Task #986). The location rules, their order and project-kit's other placement choices are recorded in its architecture decisions (ADR-056; they do not propagate); the fixed and derived paths are in the propagated references — the configuration file's in the CLI reference ("Configuration file"), a filler file's in the lifecycle README (linked above).

### The container

An artefact's front matter — for a collection entry, the entry itself — may hold **one key owned by the methodology** (`pkit:` in this distribution — [the lifecycle README, "The methodology's literals"](../lifecycle/README.md#the-methodologys-literals)). Everything under it is the methodology's; everything outside it is the artefact's own (COR-053 point 10). Inside it:

- a **functionality block** is named for a functionality and its command group — `friction` ([COR-050](../decisions/core/COR-050-anchors-and-friction.md)) is the first — and carries no version;
- a **role block** is named for a role and holds, keyed by point, the data that role's provider keeps about the artefact; every point block carries the `schema_version` of the point it targets.

```yaml
pkit:
  friction:                       # functionality block — shape owned by the backbone
    anchors: { path: [src/cli/**] }
    revalidated: { at: 2026-10-02T09:40:12Z, outcome: unchanged, unchanged-because: "…" }
  documentation:                  # role block — one point block per point, each versioned
    reading-evidence:
      schema_version: 1
      last-run: 2026-10-01
```

**How validation reads it** (COR-053 point 10). A key naming a shipped functionality is that block. Any other key is a role block only if every child is a point block carrying `schema_version`. Anything else is an unknown-key error with the nearest known key suggested — the known set is the functionality names, the active role words and their qualified forms — and a reminder that a role block needs a versioned point block. A point block at an incompatible version is inert and reported, its body unvalidated. A role block whose role has no active provider is an **orphan**: preserved and reported, never an error, validated again when a provider returns. A misspelt `frictoin:` therefore fails loudly, while a `documentation:` block left behind by an uninstalled capability waits quietly.

**Key form.** A role block's key is the role word alone, the qualifier being resolved from the active provider. The qualified form is written when two active roles share a word — the install plan that introduces the second lists the artefacts whose keys change, rewritten only with consent — and always when a role word equals a functionality block's name.

**What ships now.** `backbone/container.schema.json` — the container in both forms (a document's front matter, a collection entry), with the `friction` block modelled strictly. Its discrimination rule, the shared unknown-key renderer and the load-check live in `project_kit.backbone_schemas`; the point-version compatibility check waits on the role resolver. `backbone/config.schema.json` — the backbone configuration file (`.pkit/project/config.yaml`): `name`, `docs`, `friction`, `connections` and the reserved `project` block, unknown keys refused at every backbone-owned level, no version key. `pkit validate` applies it, with the repository checks the owning records ask for, in its configuration pass (`project_kit.config_validate`); the CLI reference's "Configuration file" section documents every key. `backbone/package.schema.json` — a component's `package.yaml`: every field in use plus the `connections`, `docs` and `friction` blocks, **permissive on unknown keys** (they warn with the nearest known key; the strict flip is #999) where the rest of the class is strict; its validator and repository checks are `project_kit.package_validate`, run by `pkit validate`'s "packages" pass and by the register pre-flight (the lifecycle README, "Validation: the package schema"). The other two schemas of the class arrive with their Tasks: rule-set files (#989), the filler envelope (#994). `pkit validate`'s friction pass discovers artefacts in the declared places and applies the container rule to them (below); the registry refactor that generalises the passes is Task #986.

### The friction block

The `friction` functionality block is what an artefact carries for [COR-050](../decisions/core/COR-050-anchors-and-friction.md): what makes it true, and when it was last revalidated against that. The record owns the keys; `container.schema.json` fixes their shape; `pkit validate` applies it.

**Where it sits — both forms.** Inside the container, in a **document's** front matter, or inside each **entry** of a collection file (a Markdown file whose front matter maps ids to entries; the entry's content is its data plus the body section headed by its id). The artefact's own fields — `id`, `status`, whatever defines it — stay outside the container.

```yaml
# a document                              # a collection file
---                                       ---
id: cli-guide                             name: cmn
pkit:                                     RS-CMN-001:
  friction:                                 status: accepted
    anchors: { path: [src/cli/**] }         pkit:
    revalidated:                              friction:
      at: 2026-10-02T09:40:12Z                  anchors: { record: [COR-050] }
      outcome: unchanged                  RS-CMN-002:
      unchanged-because: "…"                status: draft
---                                         pkit: { friction: { anchors: { artefact: [RS-CMN-001] } } }
                                          ---
                                          ## RS-CMN-001 — Name things
                                          …
```

**Fields.**

| Key | Meaning |
|---|---|
| `anchors` | What makes the artefact true, grouped by kind — `path` (files or globs relative to the repository root, `**` across folders), `record` (an identified record, such as a decision), `artefact` (another artefact by its id; a document may also be named by its repository-relative path). Each list is non-empty with unique entries. An artefact without anchors is *unanchored* — reported, never an error. |
| `revalidated` | The last revalidation, written on a person's decision. `at` — a UTC timestamp `YYYY-MM-DDTHH:MM:SSZ`; the revalidation point is the last commit in which its parsed value changed. `outcome` — `updated` or `unchanged`; `at` and `outcome` come together. `unchanged-because` — required with `outcome: unchanged`: why the content still holds against *this* change. `deferred` — one entry per anchor whose friction is deliberately postponed: `anchor: {kind, value}` plus a `reason`; kept sorted by anchor. An artefact never yet revalidated may carry `deferred` alone; an empty `revalidated` is refused. |
| `last-check` | Tool-written only, by the after-merge job: `state` (`current` / `stale` / `deferred`), `as-of` (the commit checked against), `since` (where staleness came from). Never read for friction. |

Unknown keys anywhere in the block are refused. The block carries no version; it is migrated when it changes, preserving the parsed value of `at`.

**Where artefacts are looked for.** Only in the **declared places**: the project's `friction.places` in `.pkit/project/config.yaml` (repository-relative paths or globs; a directory, or a glob ending in `**`, means every Markdown file beneath it), and each installed capability's `friction.places` in its `package.yaml`. A capability place is an object `{location, path}` — inside the named `docs.locations` entry, or repository-relative without one (the lifecycle README, "The connection, documentation and friction blocks"); today's discovery reads only string-shaped capability places and resolves them under the internal root, so object-shaped ones are not yet walked — Task #1025 aligns discovery with the schema. Front matter outside the places is never read, a plain YAML file in a place is not a document, and a match that resolves outside the repository through a link is dropped — the walk never reads a file the repository does not hold. The same reader takes the rest of the `friction` key — `mode`, `surface`, `exclude` — so the configuration is read once.

**Validation findings** (COR-050 point 12) — each fails `pkit validate`, in either mode, and names the fix:

- *unparsable front matter* in a place — reported whenever places are declared, and it keeps the pass awake, since the check never skips an artefact it cannot parse: a YAML typo in the only container-carrying file is an error, not silence;
- *a malformed block* — the container schema's or the container rule's errors, against `path` (a document) or `path#id` (an entry) and a JSON Pointer into the block;
- *a dangling deferral* — a `deferred[].anchor` matching, by kind and value, no anchor of the artefact; the pointer carries the entry's index as written;
- *a cycle between artefacts* through `anchors.artefact`, reported once with its path (`A -> B -> A`; a self-anchor is `A -> A`).

Two things the pass **reports** without failing: orphaned role blocks in the container, and *schema unavailable* — the tree has no readable container schema, so the block check was skipped (sync the tree).

The settings themselves are the **configuration pass's** findings, since it owns the file (the CLI reference, "Configuration file"): an invalid `friction.mode` (the schema's enum — never switched off silently) and a place, surface or exclude path outside the repository (absolute, climbing above the root, or resolving outside it through a link); a capability's `friction` entries are the packages pass's. The friction pass reads those settings and never walks a place that leaves the repository.

The pass is **dormant** — it prints only its counts — when no places are declared, or when nothing in them needs judging: no artefact carries the container and no file failed to parse.

**Not here.** Friction itself — the change check and the whole-repository check, dead anchors, over-broad anchors, the two measures — arrives with Tasks #990 and #991; this pass never touches git.

## Tooling expectations

A schema's value depends on tooling actually consuming the companion. Five tooling layers a schemas-using project can expect:

1. **IDE integration (zero configuration).** JSON-Schema-aware editors detect `<name>.schema.json` next to `<name>.yaml` and apply validation + autocomplete during authoring. Works out of the box; no project-specific setup.

2. **Language-level validators (consumer-driven).** Code consuming a schema may load its companion at runtime and validate the YAML before acting on it (`jsonschema` in Python, `ajv` in JavaScript, etc.). Whether a given consumer does this is a per-consumer choice — runtime validation adds latency but catches malformed data with clearer errors than a downstream crash.

3. **Pointered-instance validation (kit-level validator).** `pkit schemas validate` also validates every YAML that declares an external `$schema` against the schema that pointer names — the same binding the IDE reads, enforced in CI. See "The pointer is validated, not just classifying" above.

4. **Cross-file resolution (kit-level validator).** `pkit schemas validate` ships the resolver: it walks every typed token across every YAML, looks up each namespace's companion in the same directory, follows the companion's `x-pkit-id-collection` JSON Pointer to the id-bearing collection in the data YAML, and confirms each token's id exists. Sibling-file scope (cross-directory not supported in v1). Unresolved references are hard-rejects (validator exits non-zero); `--shape-only` skips this pass for mid-refactor authoring.

5. **Adopter-data validation (`pkit data validate <path>`).** The consumer surface for the COR-023 binding mechanism. Resolves each data file's binding (field-first; per-schema `binds_to:` as fallback), refuses on schema-version mismatch, runs JSON Schema validation against the resolved schema, and then — unless `--shape-only` — resolves cross-file typed references through the binding, scoped to the validated subtree (per COR-029). See "Adopter data → schema binding" above.

## Layout

```
.pkit/schemas/
├── README.md                  # this file — mechanism overview, conventions, patterns
├── _defs/                     # kit-wide shared $defs library (cross-file $ref target) and pointer targets
│   ├── refs.schema.json       # canonical reference_token + source patterns
│   └── process.schema.json    # the process shape contract (pointer target)
├── backbone/                  # backbone file schemas: config file, container, rule-set file, filler envelope
├── privilege-catalog.yaml     # a core-owned schema pair: data ...
├── privilege-catalog.schema.json   # ... + companion, side by side
├── harness-requirements.yaml
├── harness-requirements.schema.json
└── …                          # further core-owned pairs, one per namespace
```

This area is a **schemas home** in its own right — the core-owned one, owner name `core` — holding the pairs that belong to the core rather than to any capability (the permission model's catalogs and profiles, the harness requirements, …). It sits alongside each installed capability's `schemas/` and is walked first by every schemas verb. The `_defs/` directory holds JSON Schema fragments that every capability (and adopter project) `$ref` into. New shared patterns land as additional `$defs` in `refs.schema.json`, or as additional sibling files when a coherent group of patterns earns its own file.

## What's *not* in this area

This area defines the schemas mechanism. It does **not** decide:

- *Which contexts adopt the schemas mechanism.* That's per-adopter decisions (a COR for capabilities, a PRJ for an adopter project, etc.).
- *Overlay or customisation semantics for adopters.* When schemas are shipped by one party and customised by another, the override mechanism is a separate concern handled in a future record.

## Adopting the schemas mechanism

A context wanting to use schemas — a capability, an adopter project, a future kit feature — declares its adoption in its own record (COR for kit-shipped, PRJ for adopter-shipped). The adoption record states *why this context uses schemas* and what data it'll encode. Mechanical details (YAML format, companion convention, patterns) reference this area instead of restating them.
