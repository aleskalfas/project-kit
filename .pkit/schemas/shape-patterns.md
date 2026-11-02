---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/_defs/refs.schema.json
        - src/project_kit/schemas_validate.py
        - src/project_kit/schemas_authoring.py
      record: [COR-018, COR-019, COR-053]
      artefact:
        - .pkit/cli/README.md#schemas-validate-path
---

# Common shape patterns

The structural shapes that recur across schemas, each with the JSON Schema idiom that expresses it ([COR-018](../decisions/core/COR-018-capability-schemas.md)). Reuse the idiom, rather than invent one for each schema.

## Contents

<!-- pkit:contents -->
- [Envelope (every schema)](#envelope-every-schema)
- [Entry collections with stable ids](#entry-collections-with-stable-ids)
- [Aggregator schemas](#aggregator-schemas)
- [Reusable fragments via `$defs`](#reusable-fragments-via-defs)
<!-- /pkit:contents -->

## Envelope (every schema)

Every schema's YAML opens with the same envelope: `schema_version`, an optional `source`, then the domain's fields.

- **One definition.** The `source` envelope is defined once, as the `source` fragment of `_defs/refs.schema.json`.
- **Every companion refers to it** by `$ref`, so every schema shares one envelope shape. The stamp writes that `$ref` into each companion it stamps.

## Entry collections with stable ids

Many schemas hold a list of structured entries. Each entry carries an `id`, which a person cites and another schema's reference names.

- **What the companion checks:**
  - each entry conforms to the shape of one entry
  - `id` is required
  - no two entries share an `id`
- **What varies by schema:** the collection's name, such as `transitions`, `records`, `types` or `entries`. The shape, a list of objects that each require an `id`, is the same in every schema.
- **Where the shape lives:** in `$defs`, taking the shape of one entry as its parameter.

## Aggregator schemas

An aggregator schema collects references to entries spread across sibling files. It declares one referencing field for each namespace it collects. Each field's `$defs` constraint narrows the token to that namespace:

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

- **No entries of its own.** The aggregator points at entries, and holds none.
- **One point of contact.** A root data file serves as the single entry to a domain, without growing too long to scan. Examples are a trip that collects its transport, lodging and activities, and a project that collects its phases, deliverables and risks. The detail moves to sibling files, and the root names it.

## Reusable fragments via `$defs`

A sub-shape that several schemas need is defined once, and each schema that needs it refers to it by `$ref`. Examples are the envelope, the constraint on an entry's id, the token's pattern and a string shaped as a semantic version. One fix then mends every schema that depends on it, and the copies cannot drift apart.

Two rules settle where a fragment's canonical definition lives:

- **A pattern used across components** lives in `.pkit/schemas/_defs/refs.schema.json`. A consumer refers to it as `refs.schema.json#/$defs/<name>`. The file holds four:
  - `reference_token`, the generic `[<namespace>:<id>]` token ([COR-019](../decisions/core/COR-019-schema-reference-form.md))
  - `address_token`, the address of a role or of a point, `[<publisher>::<role>]` or `[<publisher>::<role>:<point>]` (COR-019, as [COR-053](../decisions/core/COR-053-connection-points.md) refines it)
  - `rule_citation`, the citation of a rule in data
  - `source`, the structured envelope
- **A pattern narrowed to one namespace** lives in that namespace owner's own companion, as a `$defs` entry it publishes. An example is `issue_type_ref`, for the `issue-types` namespace. A consumer refers to it across files, as `issue-types.schema.json#/$defs/issue_type_ref`. The owner is the source of truth for its own narrowed pattern.

Both rules use JSON Schema's standard `$ref` across files. `pkit schemas validate` builds a registry of every companion in the same folder and of the shared `_defs/` library. So each relative `$ref` keyed by `$id` resolves.
