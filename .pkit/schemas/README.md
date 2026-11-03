---
variant: specialized
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/_defs/**
        - .pkit/schemas/backbone/rule-set.schema.json
        - .pkit/schemas/*.yaml
        - .pkit/schemas/*.schema.json
        - src/project_kit/schemas.py
        - src/project_kit/schemas_validate.py
        - src/project_kit/schemas_authoring.py
        - src/project_kit/project_config.py
        - src/project_kit/process_authoring.py
        - src/project_kit/install.py
        - src/project_kit/rule_sets.py
        - src/project_kit/loaded_rule_sets.py
        - src/project_kit/refs.py
        - src/project_kit/friction_discovery.py
        - src/project_kit/working_tree.py
        - .pkit/lifecycle/ownership.py
      record: [COR-010, COR-017, COR-018, COR-019, COR-023, COR-029, COR-030, COR-047, COR-048, "COR-049#1", "COR-049#5", "COR-049#6", COR-051, COR-056, COR-068, COR-069, COR-070, ADR-056, ADR-057, ADR-075, ADR-076, ADR-077]
      artefact:
        - RS-OPS-019
        - RS-PM-001
        - RS-LDOC-003
        - .pkit/schemas/backbone-files.md
        - .pkit/schemas/shape-patterns.md
        - .pkit/schemas/data-binding.md
        - .pkit/schemas/backbone-files.md#what-holds-for-every-backbone-file-schema
        - .pkit/schemas/backbone-files.md#the-schemas-that-ship
        - .pkit/schemas/backbone-files.md#the-container
        - .pkit/schemas/backbone-files.md#the-friction-block
        - .pkit/schemas/backbone-files.md#answer-files
        - .pkit/schemas/backbone-files.md#rule-set-files
        - .pkit/schemas/shape-patterns.md#envelope-every-schema
        - .pkit/schemas/shape-patterns.md#reusable-fragments-via-defs
        - .pkit/schemas/data-binding.md#1-the-pkitschema-field-recommended-authoritative
        - .pkit/schemas/data-binding.md#2-per-schema-bindsto-fallback
        - .pkit/schemas/data-binding.md#resolution-order
        - .pkit/schemas/data-binding.md#schema-version-cross-check
        - .pkit/schemas/data-binding.md#cross-file-references-in-adopter-data-x-pkit-reference-namespace-cor-029
        - .pkit/decisions/README.md#two-further-id-spaces
        - .pkit/cli/README.md#schemas-validate-path
        - .pkit/cli/README.md#data-validate-path
        - .pkit/cli/README.md#new-schema-owner-name---collection-form-form---collection-name-key---no-namespace
        - .pkit/cli/README.md#config-set-key-value---yes
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#status
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#rule-sets-generate
        - .pkit/cli/README.md#rule-set-commands
        - .pkit/cli/README.md#friction-artefacts---at-rev---json
        - .pkit/cli/README.md#rule-sets-reach-path---at-rev---preview---json
        - .pkit/cli/README.md#rule-sets-altered---base-ref---head-rev---json
        - .pkit/decisions/README.md#the-acceptance-gate
        - .pkit/decisions/README.md#looking-a-citation-up
        - .pkit/lifecycle/README.md#install-pre-flight-checks
        - .pkit/lifecycle/README.md#how-the-wiring-is-resolved
        - .pkit/lifecycle/README.md#how-a-registered-anchor-kind-is-resolved
---

# Schemas

A schema is a YAML data file paired with a JSON Schema companion that declares its shape. Code reads its rules and data, kept apart from that code ([COR-018](../decisions/core/COR-018-capability-schemas.md)). This page holds the pair, its conventions, the references between schemas, the tooling, the layout, and rule sets beyond their file's shape. Three pages beside it hold the rest ("The pages beside this one" below).

<a id="when-to-reach-for-schemas"></a>

Why schemas exist, and how people use them, is in [the schemas guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/schemas/README.md).

## Contents

<!-- pkit:contents -->
- [The schema is a pair](#the-schema-is-a-pair)
- [YAML conventions](#yaml-conventions)
- [JSON Schema companion convention](#json-schema-companion-convention)
- [References between schemas](#references-between-schemas)
- [Common shape patterns](#common-shape-patterns)
- [Adopter data → schema binding (COR-023)](#adopter-data--schema-binding-cor-023)
- [Backbone file schemas and the methodology's front-matter container](#backbone-file-schemas-and-the-methodologys-front-matter-container)
- [Tooling expectations](#tooling-expectations)
- [Layout](#layout)
- [Adopting the schemas mechanism](#adopting-the-schemas-mechanism)
- [The pages beside this one](#the-pages-beside-this-one)
<!-- /pkit:contents -->

## The schema is a pair

A schema is two files, paired one to one:

| File | Carries | Read by |
|---|---|---|
| `<name>.yaml` | The instance data: the rules, the enumerations, the records | The engine code that reads the data at runtime, and people who edit the data |
| `<name>.schema.json` | The shape the YAML must have | JSON Schema validators, such as a check in CI or an editor, and people who check the shape |

Neither half alone is the schema. The YAML carries the facts, and the companion declares which facts are valid. Together they give a validator in CI, and any editor bound to the companion, one contract for whoever writes or reads the data.

## YAML conventions

Every schema's YAML follows the same envelope ([`shape-patterns.md`, "Envelope (every schema)"](shape-patterns.md#envelope-every-schema)):

```yaml
schema_version: 1   # required, first key
source:             # optional — only when the schema distills from an external spec
  upstream: <project-name>
  commit: <40-char SHA>
  decisions: [<external-decision-id>, ...]
  captured_at: YYYY-MM-DD
# …domain-specific fields…
```

- **`schema_version: <int>` is the first key, always.** The integer is the schema's own version, and the code that reads the schema switches on it when the shape changes.
- **`source:` is an optional block** that records where the schema came from, when it distills an outside specification. An example is a methodology kept in another repository. Leave the block out when the schema is its own source of truth.
- **Field names use `snake_case`,** such as `schema_version`, `captured_at` and `binds_to`.
- **Identifier values use `kebab-case`,** as the methodology's slugs do, such as `github-sub-issues` and `claude-code`.
- **Prose of several lines uses a block scalar** (`|`).
- **Comments at the top** say in plain prose what the schema is for and where it comes from. A comment beside a field stands only where the field's name does not say what it is for.

## JSON Schema companion convention

Every schema's YAML ships with a companion JSON Schema that declares its shape:

- **Its name:** `<schema-name>.schema.json`, in the same folder as the YAML. For `<root>/issue-types.yaml`, the companion is `<root>/issue-types.schema.json`. The two lie side by side, with no folder of their own.
- **Its draft:** JSON Schema `2020-12`. Every companion names it in its top-level `$schema` keyword:

  ```json
  { "$schema": "https://json-schema.org/draft/2020-12/schema", ... }
  ```

- **What it checks:** the envelope and the domain's fields. Its `properties` constrain `schema_version`, typically as `"const": <integer>`. They declare `source` as an optional object where the schema takes one, and the type and values of each domain field.
- **Required, never optional.** A schema's YAML without a companion is incomplete. Consumers and tools rely on the companion always being there.

### Which YAML the companion requirement covers

The companion requirement covers schema definitions, not every YAML file under a `schemas/` folder. A schema definition is a direct child `schemas/<name>.yaml`, paired one to one with a `<name>.schema.json` beside it.

- **Who reads only definitions:** `pkit schemas validate`, and the self-consistency check of `register`, which reuses its walk. Each lists only these files, and flags a schema definition that ships no companion.
- **Fixtures and examples** need no companion. A YAML file under any `examples/` folder, or named `*-example.yaml`, is a fixture that shows a schema, never a schema itself.
- **An instance of an outside or shared schema** needs no companion of its own either. It is a YAML file that declares a `$schema` pointer at a schema other than its own `<name>.schema.json`. The pointer is either a `# yaml-language-server: $schema=<path>` directive comment ([COR-023](../decisions/core/COR-023-schema-binds-inline.md)) or a top-level `$schema:` key. An example is a process definition, checked against the one shared `_defs/process.schema.json`.
- **A pointer at the YAML's own companion** makes an ordinary pair, so that companion is still required.

The folders under `schemas/` hold what is not a pair:

- `_defs/`: the shared library of `$defs`, and the targets of pointers
- `backbone/`: the backbone's file schemas ("The pages beside this one" below)
- `examples/`: samples

### The pointer is validated, not just classifying

An instance is free of the companion requirement, not of validation. `pkit schemas validate` checks every instance with a pointer against the schema its pointer names. It does so in its walk of the whole project, and in a run given a path. So the pointer means what it says: a definition edited by hand that breaks the shape it claims is reported.

- **Where the pointer leads from:** the YAML's own folder. That is the form the editor reads, and the form the authoring commands stamp, such as `../../../schemas/_defs/process.schema.json` from a capability's `schemas/` folder.
- **Where a finding points:** at the instance's path, with a JSON Pointer to the place that breaks the shape, such as `demo.yaml/process/subject/cardinality`. The instance is what its author edits.
- **A broken pointer is a finding, never a skip.** A target that is missing, cannot be read, is not JSON, or is no valid Draft 2020-12 schema is reported against the instance. Otherwise a contract declared with a mistyped path would leave its file unchecked, with no sign.
- **The target needs a root.** A JSON Schema whose body holds only `$defs` accepts every document. So a shared fragment meant as a pointer's target declares constraints at its root, `type`, `required` or `properties`, beside its `$defs`. A companion that refers to `#/$defs/*` across files is unaffected by those keywords.
- **Shape only.** The reference passes, of typed tokens and of `x-pkit-keys-from-namespace`, belong to pairs. They read sibling files, keyed on the YAML's stem as its namespace, and an instance has neither. References in an instance are `pkit data validate`'s, through the binding ([COR-029](../decisions/core/COR-029-adopter-data-references.md)).
- **A remote pointer, `https://…`, is free of validation too.** It cannot be read offline. The methodology's own files point at local paths, from the repository's root.
- **A top-level `$schema:` key is data,** so the target schema must admit it as a property. The same rule has the methodology's own companions declare `pkit_schema:`. The directive comment carries no such constraint.

## References between schemas

A field whose value names an entry that another schema defines writes a token that carries the namespace ([COR-019](../decisions/core/COR-019-schema-reference-form.md)). Examples are a workflow state naming its issue types, a validation rule naming its severity, and an aggregator naming sibling files' entries:

```yaml
applies_to: ["[issue-types:task]", "[issue-types:feature]"]
severity: "[validation-severity:hard-reject]"
```

The token's shape is `[<namespace>:<id>]`:

- **`<namespace>`** is the target schema's stem: its file name without `.yaml` and without `.schema.json`.
- **`<id>`** is the target entry's id within that schema's collection.
- **A scoped id** may carry one more segment, `[<namespace>:<scope>:<id>]`. It names the source that contributed an entry to a collection several sources fill, such as an installed component (COR-019). The plain form stays valid.

**A reference within one file stays bare.** An example is a transition's `from` naming a state defined elsewhere in the same workflow schema:

```yaml
transitions:
  - id: open-to-review
    from: open       # bare — same file
    to: review
```

**A mapping's keys stay bare, always,** whether they declare ids of their own namespace or name another's. A definition reads cleanly so:

```yaml
issues:
  epic:           # bare — not "[issue-types:epic]"
    required_sections: [...]
  feature:
    required_sections: [...]
```

Where a mapping's keys name another namespace, the companion carries that namespace, never each key. The parent field takes the annotation `x-pkit-keys-from-namespace: "<namespace>"`:

```json
"issues": {
  "type": "object",
  "x-pkit-keys-from-namespace": "issue-types",
  "patternProperties": {
    "^[a-z][a-z0-9-]*$": { "$ref": "#/$defs/issue_body_shape" }
  }
}
```

- **What the resolver does with it:** it walks every field that carries the annotation, and checks that each of the mapping's keys exists in the named namespace. That is the same check across files as for a token in a value.
- **Why the split:** a key's position has a natural place in the schema to declare its namespace, and a value's position has none. So a value carries a typed token, and a key stays bare under an annotation.

### Validating the token shape

The companion checks a token's shape with a `pattern` constraint. The general form is defined once, as the `reference_token` fragment of `_defs/refs.schema.json` ([`shape-patterns.md`, "Reusable fragments via `$defs`"](shape-patterns.md#reusable-fragments-via-defs)):

```json
{
  "$defs": {
    "reference_token": {
      "type": "string",
      "pattern": "^\\[[a-z][a-z0-9-]*:[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?\\]$"
    }
  }
}
```

Where a field accepts one target namespace alone, narrow the pattern's namespace half:

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

- **What the narrowed form adds:** it catches a mistyped namespace when the shape is checked, before the resolver runs.
- **How a field uses either:** its constraint refers to the fragment by `$ref`, as `#/$defs/<name>`.
- **What JSON Schema cannot check:** it does not look across files. Whether the token's id exists in the named namespace is for the code that reads the data, or for a validator that reads across files. `pkit schemas validate` runs that resolver by default ("What the resolver pass checks" below).

### Declaring where ids live: `x-pkit-id-collection`

To resolve a token such as `[issue-types:task]`, the resolver must know where in `issue-types.yaml` the ids live. Every schema that owns a namespace declares it, in an annotation at the companion's top level:

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

The value is a JSON Pointer (RFC 6901) into the data YAML. `/types` points at the top-level `types` mapping, and `/items` at a top-level `items` list. A nested pointer works too, such as `/groups/0/entries`.

The resolver reads two shapes of collection:

- **A mapping,** whose keys are the ids. In `types: { task: {...}, feature: {...} }`, the ids are `task` and `feature`. Most of the methodology's schemas use this shape.
- **A list of objects with an `id` field,** whose values are the ids. In `items: [{ id: alpha, ... }, { id: beta, ... }]`, the ids are `alpha` and `beta`. Use this shape where the entries need a stable order, or where other data on each entry makes the mapping awkward.

A schema that owns no namespace leaves the annotation out. Examples are an aggregator that names others' ids, and a schema of settings with no entries of its own. A token that names such a schema is a resolver error.

### What the resolver pass checks

`pkit schemas validate` runs two passes by default:

1. **Shape.** JSON Schema checks the YAML's structure.
2. **References,** in two walks:
   - **Tokens in values.** For each string in a value that matches `[<namespace>:<id>]`, the resolver finds the namespace's companion in the same folder. It follows the companion's `x-pkit-id-collection` pointer into the data YAML, and checks that the id is there. A scoped token, of three segments, is checked for its shape only.
   - **Keys under an annotation.** For each field of the companion that carries `x-pkit-keys-from-namespace: "<namespace>"`, the resolver walks to that field in the data. It checks that each key exists in the named namespace's collection.

- **A resolver error fails the run,** which exits non-zero.
- **`--shape-only`** skips the reference pass, for an author in the middle of a refactor.
- **Sibling files only.** The resolver reads the companions in the same folder, and no other folder's.

## Common shape patterns

The shapes that recur across schemas, each with the JSON Schema idiom that expresses it, are on [`shape-patterns.md`](shape-patterns.md). Each heading below leads to its section there.

### Envelope (every schema)

See [`shape-patterns.md`, "Envelope (every schema)"](shape-patterns.md#envelope-every-schema).

### Entry collections with stable ids

See [`shape-patterns.md`, "Entry collections with stable ids"](shape-patterns.md#entry-collections-with-stable-ids).

### Aggregator schemas

See [`shape-patterns.md`, "Aggregator schemas"](shape-patterns.md#aggregator-schemas).

### Reusable fragments via `$defs`

See [`shape-patterns.md`, "Reusable fragments via `$defs`"](shape-patterns.md#reusable-fragments-via-defs).

## Adopter data → schema binding (COR-023)

An adopter's data file binds to a capability's schema by a `pkit_schema:` field in the file. Without one, a `binds_to:` glob the schema declares binds it ([COR-023](../decisions/core/COR-023-schema-binds-inline.md)). The binding is on [`data-binding.md`](data-binding.md), and each heading below leads to its section there.

### 1. The `pkit_schema:` field (recommended, authoritative)

See [`data-binding.md`, "1. The `pkit_schema:` field (recommended, authoritative)"](data-binding.md#1-the-pkit_schema-field-recommended-authoritative).

### 2. Per-schema `binds_to:` fallback

See [`data-binding.md`, "2. Per-schema `binds_to:` fallback"](data-binding.md#2-per-schema-binds_to-fallback).

### Resolution order

See [`data-binding.md`, "Resolution order"](data-binding.md#resolution-order).

### Schema-version cross-check

See [`data-binding.md`, "Schema-version cross-check"](data-binding.md#schema-version-cross-check).

### `pkit data validate <path>`

See [`data-binding.md`, "`pkit data validate <path>`"](data-binding.md#pkit-data-validate-path).

### Cross-file references in adopter data: `x-pkit-reference-namespace` (COR-029)

See [`data-binding.md`, "Cross-file references in adopter data"](data-binding.md#cross-file-references-in-adopter-data-x-pkit-reference-namespace-cor-029).

### Authoring

See [`data-binding.md`, "Authoring"](data-binding.md#authoring).

## Backbone file schemas and the methodology's front-matter container

The backbone file schemas are the schemas of the files the backbone validates but does not write. Each such file binds to its schema by where it lies, never by a field in it. They are on [`backbone-files.md`](backbone-files.md), with the six schemas under `backbone/`. Five are for such files, and the sixth for package metadata, whose file no location rule binds. Each heading below leads to its section there.

### The container

The one key of an artefact's front matter that the methodology owns, `pkit:`, with its functionality blocks and role blocks. See [`backbone-files.md`, "The container"](backbone-files.md#the-container).

### The friction block

The `friction` block an artefact carries in its container: its anchors, or the reason it has none. See [`backbone-files.md`, "The friction block"](backbone-files.md#the-friction-block). Its parts there:

- [Where it sits](backbone-files.md#where-it-sits)
- [Fields](backbone-files.md#fields)
- [The block holds no answer](backbone-files.md#the-block-holds-no-answer)
- [Where artefacts are looked for](backbone-files.md#where-artefacts-are-looked-for)
- [A place may give a type](backbone-files.md#a-place-may-give-a-type)
- [A place may declare links](backbone-files.md#a-place-may-declare-links)
- [A place may declare derived links](backbone-files.md#a-place-may-declare-derived-links)
- [What an older backbone does with them](backbone-files.md#what-an-older-backbone-does-with-them)
- [Validation findings](backbone-files.md#validation-findings)
- [What the pass warns of and reports](backbone-files.md#what-the-pass-warns-of-and-reports)
- [The configuration's own findings](backbone-files.md#the-configurations-own-findings)
- [When the pass is dormant](backbone-files.md#when-the-pass-is-dormant)
- [Rule-set files in the friction pass](backbone-files.md#rule-set-files-in-the-friction-pass)
- [What the friction pass leaves to others](backbone-files.md#what-the-friction-pass-leaves-to-others)

### Answer files

The files in which a change keeps its answers to friction, in the folder `.pkit/project/friction/answers/`. See [`backbone-files.md`, "Answer files"](backbone-files.md#answer-files).

### Rule-set files

A rule set ([COR-051](../decisions/core/COR-051-rule-sets.md)) is one Markdown file. Its front matter holds the data, and its body one section for each rule. `backbone/rule-set.schema.json` fixes the data's shape. `pkit validate` applies it, with every check below, in its `rule-sets` pass, `project_kit.rule_sets`.

- **The file's shape,** its front matter, its body and its ids, is on [`backbone-files.md`, "Rule-set files"](backbone-files.md#rule-set-files).
- **Where the files lie, and how their rules bind,** are below.

#### Where they are: the location rule

A file is a rule-set file because of where it is, and nothing in the file binds it. A folder named `rule-sets` holds rule sets:

| Folder | Holds | The set is cited |
|---|---|---|
| `.pkit/rule-sets/` | the backbone's method rule sets, its loaded set `OPS` among them | `backbone:<SET>` |
| `.pkit/capabilities/<name>/rule-sets/` | an installed capability's method rule sets, shipped, versioned and synced with it | `<name>:<SET>` |
| `rule-sets/` under the internal documentation root (`docs/rule-sets/` by default, [COR-049](../decisions/core/COR-049-documentation-roots.md)) | the project's rule sets | bare, `<SET>` |
| any declared place, the project's or a capability's, whose path has a `rule-sets` segment | more project rule sets, wherever the project keeps them | bare |

- **Which files:** every Markdown file in or beneath such a folder is a rule-set file, except its `README.md`, which is the folder's signpost.
- **A file two folders reach** belongs to the first in the table's order.
- **A file there with no front matter,** or front matter that does not parse, is a finding, never skipped.
- **Who writes them:**
  - **Method rule sets** are refreshed by sync, with their component. A project never edits one: it inherits it.
  - **Project rule sets** are the project's. Sync never reads or writes one, and uninstall never writes one (COR-051 point 6).
  - **A capability's install** creates the one project rule set the capability declares, in `rule-sets/` under the internal documentation root. That capability's migration may create it for an earlier install (COR-017, [the lifecycle reference, "Install pre-flight checks"](../lifecycle/README.md#install-pre-flight-checks), "The declared project rule set").

#### When the internal root changes

The folder under the internal documentation root follows the root as it stands (COR-051 point 6). A change made through the command keeps every set in that folder found, and validation catches a change made by hand:

- **`pkit config set docs.internal <path>`** declares the old folder as a place. The location rule might not claim a rule-set file of `<old root>/rule-sets/` under the new root. Then the same write adds that folder to `friction.places`, under the one consent ([the CLI reference, "config set"](../cli/README.md#config-set-key-value---yes)). A declared place, the table's last row, then finds the sets where they are.
- **An edit of `docs.internal` by hand** runs no command, so nothing declares the folder. The `rule-sets` pass then fails on each file left behind, as `unfound-rule-set` (below).
- **Moving the sets under the new root** is the project's own step. Move the files, then remove the old folder from `friction.places`. Until then, the sets stay found where they are (COR-049 point 6).
- **Another rule-set folder under the root** is not declared by the change. A capability place whose location derives from the root moves with the root until that location is recorded (COR-049 point 5). A file left behind there is `unfound-rule-set` too.

#### Loaded sets

A loaded set keeps operational rules, the rules every session loads (COR-068, [COR-070](../decisions/core/COR-070-capability-loaded-rules.md)).

- **The backbone's** is `OPS`, `.pkit/rule-sets/ops.md`, whose loaded file is `.pkit/rules/core.md`. The rules area's README describes both.
- **A capability's,** where it ships one, sits in its `rule-sets/` folder. Its loaded file is its `rules.md`, and the capabilities' rules index reaches it.
- **Where its rules bind:** on what a session does, not on files. So it takes none of the parts that say where a rule binds.

**The schema refuses on a set marked loaded** what the file alone shows:

- `scope`, `inherits` and `checks`
- `offers` or `fills` on any rule

**The `rule-sets` pass refuses** what needs other files:

- **`inherits-loaded`:** a set whose `inherits` names a loaded set.
- **`second-loaded-set`:** a second loaded set of the backbone, of a capability or of the project, after the first by path. An owner has one, so "core rule 19" names one rule.
- **`loaded-heading`:** a first-level heading in the set's body, since the loaded file is included under the host's heading.
- **`loaded-import-token`:** a token outside code that opens with the import prefix a registered adapter's `entry:` declares, for Claude Code `@`. It is read in any loaded set's statements and prose, core's included. A session that loads the file could read such a token as an import of its own.
  - **A path in backticks** is code, and stays.
  - **Where no registered adapter declares an `entry:`,** nothing is refused.
- **`loaded-preface` and `loaded-file-orphaned`,** where a capability is authored:
  - the loaded set's preface, the prose before its first rule, that does not name the capability
  - a `rules.md` at the capability's root with no loaded set behind it

**The loaded file** is generated from the set by `pkit rule-sets generate`.

- **Where it goes:** the backbone's goes to `.pkit/rules/core.md`, a capability's goes to `.pkit/capabilities/<name>/rules.md`, and a project's own goes to `.pkit/rules/project.md`. The set's owner fixes where it goes, never a key.
- **What it holds:** the set's body, with each accepted rule's section under the heading `N. Title (RS-<SET>-NNN)`, at the level the set writes it. It leaves out the front matter, and each other rule's section.

**Kept in step** (`loaded-file-stale`, an error). Where the set is authored, the pass compares the loaded file with the generator's output, byte for byte, once line endings are read as `\n`. A file that differs, or is missing, fails.

- **Where the set is authored** is asked of the tree's own predicate, `is_synced_copy`.
- **Where the set arrives by sync,** the project receives both files together, and the pass compares neither.
- **A tree without the ownership module** cannot tell. The pass skips the comparison, and reports that it did (`loaded-file-unchecked`).

**Its budget** (COR-069). `budget`, at the top of the front matter beside `loaded: true`, bounds the loaded file's words.

- **What fails:** the pass counts the loaded file as written. It fails a file past its budget where the set is authored, and always for the project's own set (`rules-file-over-budget`).
- **A missing budget:** where it is authored, a component's loaded set that gives no `budget` fails (`loaded-set-without-budget`).
- **Where the set arrives by sync,** its file's count is reported, and fails nothing.
- **Elsewhere:** how a word is counted, and the summary line of each rules file, are the CLI reference's ("validate"). Where each budget is set, and how a change raises it, are the rules area's README's.

**The rest:**

- **What holds as for every set:** the other keys, the join, ids, origins and successors. A loaded rule is an artefact, so a change to it is friction for what anchors to it.
- **Where it binds:** no route starts at a loaded set or passes through one (below). So the rule-set reviewer, and every check of one artefact, judge no artefact against a loaded rule.
- **Citing a loaded rule:** by its id, such as `backbone:RS-OPS-019`, or a capability's `project-management:RS-PM-001`. Core's, and a project's own, may be cited by layer and number too, as "core rule 19" ("Citing a rule" below). A capability's rule has no form by layer and number (COR-070 point 1).
- **How it reaches a session** is checked in the same pass (`loaded-rules-undelivered`, the CLI reference, "validate"). The check reads the capabilities' rules index, and the host file each registered adapter declares.

#### Statuses

Each status says whether a rule binds (COR-051 point 4):

- **A proposed rule** binds nothing.
- **An accepted rule** binds where a route reaches its set (below). Writers and checks follow it.
- **A superseded rule** names its successor, and binds nothing.
- **A withdrawn rule** is retired without a successor, and binds nothing.

Accepting a rule is a reviewed change, as accepting a decision record is ([the decision-record specification, "The acceptance gate"](../decisions/README.md#the-acceptance-gate)).

#### Citing a rule

A rule is cited as `RS-<SET>-NNN`, or `RS-<SET>-NNN#<point>` for an extension point. The owning component goes in front for a method rule set.

- **In prose:** in brackets, as a capability's decision is cited, such as `[living-docs:RS-LDOC-003]`.
- **In data:** with no brackets, such as `living-docs:RS-LDOC-003`.
- **A bare id** resolves too, since set names are unique. A component, when written, must be the one that owns the set.

**What reads a citation:**

- **`pkit refs validate`** resolves every citation of a rule in an agent's or a skill's body, except a loaded set's. The check under "Citing an operational rule" reads that one.
- **`pkit refs lookup <citation>`** prints where the rule lives ([the decision-record specification, "Looking a citation up"](../decisions/README.md#looking-a-citation-up)).
- **`refs.schema.json#/$defs/rule_citation`** checks the citation's shape in data.
- **`pkit decisions validate`** reports a rule id claimed twice across the rule sets ([the decision-record specification, "Two further id-spaces"](../decisions/README.md#two-further-id-spaces)).

#### Citing an operational rule

A rule of a loaded set is cited by its id, as any rule is (COR-068 point 6). Core's, and a project's own, may also be cited by layer and number:

- **`core rule 19`** names `backbone:RS-OPS-019`.
- **`project rule N`** names a rule of the project's own loaded set.
- **A capability's rule** is cited by its id with the capability's name, `<capability>:RS-<SET>-NNN`. No form of capability and number exists (COR-070 point 1).

Validation's `refs` member reads both forms. It warns of a citation of a rule the set lacks, and of a superseded or withdrawn one, naming its successor. The forms it reads, and the files it reads them in, are the CLI reference's ("validate").

#### What the pass checks

Errors fail `pkit validate`, and reports print under its `rule-sets` heading.

- **The file:** unreadable, no front matter, or front matter that does not parse or is not a mapping. A key written twice, a rule id written twice in `rules` among them, is a duplicate. The schema's errors come with unknown keys suggested.
- **A rule-set file left behind** (`unfound-rule-set`, COR-051 point 6). It is an error on a Markdown file the location rule leaves unclaimed, though it reads as a set. Its rules bind nothing. Such a file:
  - lies in or beneath a folder named `rule-sets`, and is not that folder's `README.md`
  - has front matter that names a set (`rule-set:`)
  - is typically one a root changed by hand left behind
- **The join:** every rule in `rules` has a section headed by its id, and every section has an entry. No id heads two sections, and no heading opens like an id without being one.
- **Ids and names:** every id is well formed, and carries the file's set name. An id of an inherited set is a redefinition. No two rule sets share a name.
- **The container** inside each rule: the container schema and rule, read against the active wiring, as for any artefact ([`backbone-files.md`, "The container"](backbone-files.md#the-container)). An orphaned role block or an inert point block is a report.
- **Origins** (COR-051 point 5): every accepted rule has a complete origin. A cited decision record exists, and is accepted whenever the rule is. A cited source resolves through the anchor kind a capability registers for it ("Origins and their sources" below).
- **Successors:** each exists, in the same set or in a set that inherits it, and is not the rule itself.
- **Check parts** (COR-051 point 2):
  - **An error:** a part declared under `checks` for a rule the set does not hold. A rule's owner declares the part beside the rule.
  - **A report, which fails nothing:** a check that is not there. That is a backbone check that names no `pkit` command, or a component's command no installed component registers. That part then goes back to whoever judges the rest of the rule.
  - **A project's own tool** is trusted by its name.
- **Inheritance** (COR-051 point 7): the pins, the fills and the anchors of a filling rule ("Inheritance and fills" below).
- **Loaded sets** (COR-068): the refusals, the check of the loaded file and the check of its budget (COR-069), under "Loaded sets" above.
- **Conflicts between routes** (COR-051 point 7): read from the reach walk's answer at the working tree (below). Each is an error on the artefact, naming both routes. There are two:
  - an artefact reached through routes that pin one set at different majors
  - an artefact whose most specific sets bring different fills for one extension point, a fill against none included

**Where `unfound-rule-set` looks.**

- **What it reads:** the one listing of the working tree that discovery reads. In a git work tree, a file git ignores is never read, such as an installed package's copy. Outside one, every file is listed.
- **What it skips:** the folders the location rule names for method rule sets, `.pkit/rule-sets/` and `.pkit/capabilities/*/rule-sets/`, whether the capability is installed or not. In the methodology's source repository, a capability not installed keeps its method sets there.
- **The fixes it names:** add the folder to `friction.places`, or move the file under the internal root's `rule-sets/`. For a file meant as no rule set, such as an example, move it out of a `rule-sets` folder, or remove its `rule-set:` key.
- **What it leaves out:** a file whose front matter does not parse, or names no set. Nothing in such a file says it was meant as a set.
- **What it never does:** decide that a file is a rule set. The front matter serves only to find the file, and where a file lies decides whether it is one.

**Origins and their sources.** The pass looks a source's kind up in the one registry of anchor kinds that the friction checks read. It takes the verdict an anchor of that kind gets there.

- **A kind nothing registers** is unresolved.
- **A kind two capabilities register** is refused. So is a registered resolver whose command names no leaf, or does not declare the query contract.
- **The backbone's own kinds,** `path`, `record` and `artefact`, are anchor kinds, never source kinds.
- **How a source is resolved:** this pass runs no resolver of its own. The registry's resolver resolves a source of a kind that passes, run as the friction checks run it ([the lifecycle reference](../lifecycle/README.md#how-a-registered-anchor-kind-is-resolved)).

A source is never silently passed:

- **Its resolver names a file for it:** it resolves.
- **Its resolver names no file for it:** an error, `missing-source`. The citation is the project's to correct.
- **Its resolver gives no answer:** an error, `unanswered-source`. An abnormal exit, a timeout, an environment not provisioned, or output in another shape gives no answer.
  - **Why it fails:** a resolver that ran and gave no answer has not resolved the source. So validation fails, rather than pass a source nobody checked.
  - **What the finding says:** to run again, after `pkit sync`, where the resolver overran or is not provisioned. Otherwise it names the resolver to mend.
- **Its kind is unresolved or refused,** so no resolver may run: it is reported as an unresolved kind. That is a report rather than an error, COR-051 point 5's one exception, because the project could do nothing to fix it in a file. A refused registration fails once, at the registration, in the packages pass.

**Inheritance and fills** (COR-051 point 7).

- **The pins:** a pinned set exists under the address written: a method set with its component, a project set bare. No cycle forms.
- **Who may inherit what:**
  - a method rule set never inherits a project one
  - the backbone's inherits only the backbone's
  - any capability's may inherit the backbone's
  - a capability's inherits another capability's only if its `package.yaml` declares that capability in `requires_capabilities` as a required entry, without `optional: true` ([COR-030](../decisions/core/COR-030-capability-dependencies.md))
- **A fill** names a point that a rule of an inherited set offers. Each point is filled at most once along the chain: the set and everything it inherits, each set once. A second fill is reported where it arrives.
- **A filling rule anchors to the rule it fills,** so that a change to the inherited rule flags the fill as friction.
  - **Its anchor:** its `artefact` anchors name that rule, bare or as it is cited (`living-docs:RS-LDOC-003`), never one of its points.
  - **A fill whose rule carries no such anchor** is an error at the fill, naming the anchor to add.
- **A superseded or withdrawn rule** binds nothing, so its own fills are neither checked nor counted.
- **A fill of a superseded or withdrawn rule** is reported as orphaned, and no anchor is asked of it. It is to be removed.

#### The pinned major

The pinned major is a version relation. It is checked and reported with the others, under the `versions` heading of `pkit validate` ([the lifecycle reference, "How the wiring is resolved"](../lifecycle/README.md#how-the-wiring-is-resolved), "Version relations").

- **A pin whose major is not the inherited set's** is an error on the inheriting set. It names the new major: the set is at `2.1.0`, so update the pin to `CMN@2`. It stands until the set's owner reviews what changed, and updates the pin.
- **`pkit status` shows the same pins,** under its `Rule sets` heading, from the same check ([the CLI reference, "status"](../cli/README.md#status)). It shows each inheriting set whose pin is behind, the version the inherited set is at, and the fix. The fix is the edit to `inherits` that re-pins it, such as `DOC pins CMN@1; CMN is at 2.1.0`, then ``fix: review what changed in CMN, then update the pin to CMN@2 in `inherits` of docs/rule-sets/doc.md``.
- **No command re-pins:** the review is the point. Until the pin is updated, no rule binds through it (below).

#### Where an accepted rule binds

The backbone answers, for each artefact, which accepted rules bind on it, with one walk over one state (COR-051 point 7). Validation, the reading commands and every other reader take that one answer.

- **A route** starts at a set of the project's own whose scope selects the artefact. `pkit friction artefacts --json` names such sets on each artefact, as `artefacts[].in_scope_of`.
  - **It follows** what the set inherits, pin by pin.
  - **It passes** only through sets whose own scope, where they have one, also selects the artefact. So an inherited rule binds within the scope of the set that inherits it.
  - **A set with no scope** binds only through the sets that inherit it. A parent with a scope of its own keeps it.
- **A method rule set** takes no scope, so it starts no route. Its rules bind only through a set of the project's own that inherits it, directly or not.
- **A loaded set** starts no route, and is no parent on one, even where validation refuses a scope or an inheritance on it. So no loaded rule binds on an artefact, and `pkit rule-sets reach` names none (COR-068 point 2). `pkit rule-sets altered` still lists a loaded rule a change alters, as an artefact.
- **An accepted rule binds** on the artefact when a route leads to its set, and no pin on that route is behind its set.
  - **Behind:** a pin whose major is older than the set's.
  - **Ahead:** a pin ahead of its set is not behind it, though the version relations report it as not holding.
  - **Held back:** a rule reached only through a pin behind its set binds nothing. The answer names it as held back, with the pins that hold it.
- **A successor** binds wherever its own set is reached. The rule it replaces binds nothing.
- **A fill** binds only where the rule it fills binds through the filling set, and only while both are accepted.
  - **Several sets:** where the offering rule binds through several sets whose scopes select the artefact, the most specific of them decide the point. Those are the ones no other of them inherits.
  - **Different fills:** where they bring different fills, a fill against none included, no fill binds. The answer names the conflict, and validation fails.
  - **Each set's fill:** each brings the fill its chain holds, whatever the chain's pins, where that fill binds through the filling set.
  - **A rule that fills** binds only as a fill. So one whose fill names no point an inherited rule offers binds nowhere.
- **Two routes that pin one set at different majors** fail validation too, and the answer names that conflict.

**The commands that give the answer** ([the CLI reference, "Rule-set commands"](../cli/README.md#rule-set-commands)):

- **`pkit rule-sets reach`** gives the answer at the working tree, or at a commit. Given paths, it answers only for the artefacts at them, with the text of each rule that binds there. A writer reads that first.
  - **With `--preview`,** it gives where rules would bind if every proposed rule were accepted, marking what holds only under the preview. Validation never reads that answer ([the CLI reference, "rule-sets reach"](../cli/README.md#rule-sets-reach-path---at-rev---preview---json)).
- **`pkit rule-sets altered`** gives the answer at the base and at the head for each artefact a change altered. It gives it too for each artefact the change brought under a rule without altering it, with those rules ([its section](../cli/README.md#rule-sets-altered---base-ref---head-rev---json)).
- **The state read:** the rule-set files are read at that state, through the tree discovery reads it by.

A tree without the rule-set schema, one recorded before the schema landed, skips the kind, and says so.

#### What the rule-set pass leaves to others

- **Judgment, for agents and reviewers** (COR-051 points 5 and 7): whether a quoted reason supports its rule. Whether an inheriting set contradicts or relaxes what it inherits, beyond the mechanical checks.
- **The friction checks:** whether the anchor of a filling rule resolves, and whether it carries friction. This pass asks only that the anchor names the rule filled.
- **The registry of anchor kinds:** how a registered resolver is run, and the answer it gives, for anchors and sources alike. A source goes through the same registry, verdict and run as an anchor.

## Tooling expectations

A schema is worth what the tools that read its companion make of it. A project that uses schemas can expect five layers:

1. **An editor, through a pointer.** An editor that reads JSON Schema checks a YAML file and completes its fields while it is written. It finds the schema only through the file's `# yaml-language-server: $schema=<path>` directive, its top-level `$schema:` key, or the editor's own settings. It pairs no `<name>.schema.json` with the `<name>.yaml` beside it by itself.
   - **The configuration file** carries the directive, which `pkit config set` writes.
   - **A process definition** carries one that its stamp writes, pointing at the shared process schema.
   - **A schema stamped by `pkit new schema`** carries none.
2. **Validators in the code that reads a schema.** Such code may load the companion at runtime, and check the YAML before acting on it, with `jsonschema` in Python or `ajv` in JavaScript. Each consumer chooses. A check at runtime adds time, and reports malformed data more clearly than a later crash does.
3. **Validation of instances, by a validator of the methodology.** `pkit schemas validate` also checks every YAML file that declares an outside `$schema` against the schema its pointer names. It enforces in CI the binding an editor reads ("The pointer is validated, not just classifying" above).
4. **Resolution across files, by a validator of the methodology.** `pkit schemas validate` runs the resolver over every typed token and every annotated key ("What the resolver pass checks" above).
5. **Validation of adopter data,** by `pkit data validate <path>`. It resolves each data file's binding, refuses a mismatched `schema_version` and checks the file against the schema bound to it. Then, unless given `--shape-only`, it resolves the typed references across files, within the folder validated ([`data-binding.md`](data-binding.md)).

## Layout

This folder holds the reference's pages, the shared library, the backbone file schemas and the pairs the core owns:

```
.pkit/schemas/
├── README.md                  # this file — the mechanism, its conventions, the references, rule sets
├── backbone-files.md          # the backbone file schemas, the container, the friction block, answer and rule-set files
├── shape-patterns.md          # the common shape patterns
├── data-binding.md            # how adopter data binds to a schema
├── _defs/                     # the shared $defs library (target of $ref across files) and pointer targets
│   ├── refs.schema.json       # reference_token, address_token, rule_citation and source
│   └── process.schema.json    # the process shape contract (pointer target)
├── backbone/                  # the backbone file schemas: configuration, container, filler envelope,
│                              #   answer file, package metadata, rule-set file
├── privilege-catalog.yaml     # a schema pair the core owns: data ...
├── privilege-catalog.schema.json   # ... + companion, side by side
├── harness-requirements.yaml
├── harness-requirements.schema.json
├── harness-support.yaml       # the shape of each adapter's support declaration (COR-047)
├── harness-support.schema.json
└── …                          # further pairs the core owns, one per namespace
```

This area is a home of schemas in its own right: the core's, whose owner name is `core`.

- **What it holds:** the pairs that belong to the core rather than to a capability. Examples are the permission model's catalogs and profiles, the harness requirements ([COR-047](../decisions/core/COR-047-harness-requirement-declaration.md)), and the shape of each adapter's answers to them.
- **Its place among the homes:** it sits beside each installed capability's `schemas/` ([COR-017](../decisions/core/COR-017-capability-pattern.md)), and every schemas verb walks it first.
- **`_defs/`** holds the JSON Schema fragments that each capability, and each adopter project, refers to by `$ref`. A new shared pattern lands as a further entry of `refs.schema.json`'s `$defs` ([`shape-patterns.md`](shape-patterns.md#reusable-fragments-via-defs)). A coherent group of patterns may earn a sibling file of its own.
- **What ships:** the whole folder, to every project, refreshed by each sync.

## Adopting the schemas mechanism

<a id="whats-not-in-this-area"></a>

This area defines the schemas mechanism, and decides nothing about which context uses it.

- **Who adopts it, and why:** a context that uses schemas declares that in a record of its own. Such a context is a capability, a project or a later part of the core. Capabilities adopt it in COR-018. The record says why the context uses schemas, and what data they will hold.
- **Which record:** a core record for a context the methodology ships, and a record of the project's own for a context the project ships.
- **What the record leaves to this area:** the mechanics, such as the YAML format, the companion convention and the patterns. The record refers to this area, rather than state them again.

## The pages beside this one

- [Backbone file schemas](backbone-files.md): the schemas of the files the backbone validates but does not write, and how each binds by its location. They cover the container in an artefact's front matter, the friction block, answer files and rule-set files.
- [Common shape patterns](shape-patterns.md): the envelope, entry collections with stable ids, aggregator schemas and fragments shared through `$defs`.
- [Binding adopter data to a schema](data-binding.md): the `pkit_schema:` field, the `binds_to:` fallback, the order of resolution and the version check. It covers `pkit data validate`, and references across adopter data files too.
