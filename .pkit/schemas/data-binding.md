---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/data_validate.py
        - src/project_kit/schemas_authoring.py
        - src/project_kit/answer_files.py
        - .pkit/skills/core/schema/schema.md
        - .pkit/skills/core/schema/author.md
        - .pkit/skills/core/schema/extend.md
      record: [COR-010, COR-017, COR-019, COR-020, COR-022, COR-023, COR-029, "COR-062#2"]
      artefact:
        - .pkit/cli/README.md#data-validate-path
        - .pkit/cli/README.md#schemas-validate-path
        - .pkit/cli/README.md#new-schema-owner-name---collection-form-form---collection-name-key---no-namespace
        - .pkit/cli/README.md#validate
---

# Binding adopter data to a schema

How an adopter's data file finds the capability schema that judges it, and how `pkit data validate` checks it ([COR-023](../decisions/core/COR-023-schema-binds-inline.md), which supersedes [COR-022](../decisions/core/COR-022-schema-data-binding.md)). A capability's schema is read in two ways:

- **By the capability's own engine,** which reads the schema's YAML at runtime. The file lies at `<capability>/schemas/<schema>.yaml`, so the engine knows what to read, and nothing binds it.
- **By adopter data files that follow the schema,** such as `trips/<slug>/trip.yaml`, which follows `trip-planning:trip`. Such a file needs a binding that says which schema applies to it. The resolver, the editor and `pkit data validate` each read that binding.

The binding has two layers: a field in the data file, and a fallback the schema declares.

## Contents

<!-- pkit:contents -->
- [1. The `pkit_schema:` field (recommended, authoritative)](#1-the-pkit_schema-field-recommended-authoritative)
- [2. Per-schema `binds_to:` fallback](#2-per-schema-binds_to-fallback)
- [Resolution order](#resolution-order)
- [Schema-version cross-check](#schema-version-cross-check)
- [`pkit data validate <path>`](#pkit-data-validate-path)
- [Cross-file references in adopter data: `x-pkit-reference-namespace` (COR-029)](#cross-file-references-in-adopter-data-x-pkit-reference-namespace-cor-029)
- [Authoring](#authoring)
<!-- /pkit:contents -->

## 1. The `pkit_schema:` field (recommended, authoritative)

An adopter data file carries a top-level `pkit_schema:` field. Its value is the bare two-part form `<capability>:<schema-name>`:

```yaml
# yaml-language-server: $schema=.pkit/capabilities/trip-planning/schemas/trip.schema.json
pkit_schema: trip-planning:trip
schema_version: 1
slug: japan-2026
title: Japan (Tokyo)
# …
```

- **No brackets.** The value is the bare reference. [COR-019](../decisions/core/COR-019-schema-reference-form.md)'s brackets delimit a reference set in prose or in another value, where text surrounds it. Where the whole value is the reference, the brackets add nothing.
- **Optional, and authoritative.** The field is recommended. Where it is present, the resolver uses it, and reads no capability's fallback.
- **The editor's counterpart.** The YAML Language Server's directive comment, `# yaml-language-server: $schema=...`, binds the file for an editor. An editor with no `pkit` support then completes and checks the file as it is written.
- **Two declarations.** The field serves `pkit`, and the directive serves the editor. Nothing writes the two together, so whoever writes the file keeps them in step.

## 2. Per-schema `binds_to:` fallback

A capability's schema declares the adopter files it judges in a top-level `binds_to:` field of the schema's YAML. The field lists globs, each matched against an adopter file's path from the repository root:

```yaml
# .pkit/capabilities/trip-planning/schemas/trip.yaml
schema_version: 1
binds_to:
  - "trips/*/trip.yaml"
# … rest is the schema's namespace content
```

- **On the schema itself.** The field lives on the schema, never in a separate registry of bindings. A binding goes with its schema when the schema is removed, and no second file needs keeping in step.
- **The companion permits it.** The companion's `properties` declare `binds_to` like any other field, since the shape pass judges the schema's YAML against it. Its `properties` declare `pkit_schema` too, as a field no data file must carry, wherever adopter files carry one.
- **How a glob matches.** A glob is matched with the semantics of Python's `fnmatch`. Its `*` crosses `/`, unlike a shell's per-segment matching. `**/<name>` is the idiom the shipped capabilities use for "anywhere in the tree".
- **Optional.** Most schemas own a namespace or serve their capability alone, and declare no `binds_to:`. The field matters only for a schema that describes adopter data files.
- **The walk.** Where an adopter file has no `pkit_schema:` field, the resolver walks each installed capability's `schemas/*.yaml` and reads their `binds_to:` globs. Within one capability, the first glob that matches binds the file. Matches in two capabilities make the binding ambiguous, and the adopter resolves it by adding the field.

**Pick a glob narrow enough that nothing else in an installed tree matches it.** The two kinds of collision fail differently:

- **A distinctive file name,** such as `workstreams.yaml` or `substrate-map.yaml`, is specific on its own. So `**/<name>.yaml` suffices.
- **A generic file name,** such as `config.yaml` or `settings.yaml`, is not. Narrow it with the path segments that tell it apart, such as `**/<capability>/project/config.yaml`, or rely on the adopter's `pkit_schema:` field.
- **A collision with another capability's glob** is refused as an ambiguous binding.
- **A collision with a file of no capability** is not refused. The file binds to the wrong schema, and validation reports a false failure on a correct file.

## Resolution order

The resolver binds one adopter data file in this order:

1. **Field first.** Where the file carries `pkit_schema: <capability>:<schema>`, the resolver resolves the field, which is authoritative.
2. **Capability fallback.** Otherwise, the resolver walks the installed capabilities in the order of their names. It matches the file's path from the repository root against each `binds_to:` glob of each capability's `schemas/*.yaml`.
3. **Refuse.** With no field and no matching glob, the resolver reports that the file has no schema binding. The finding names the two ways to declare one.

## Schema-version cross-check

A data file's `schema_version` names the version of the schema the data was written against. The capability's `<schema>.yaml` names the schema's current `schema_version`.

- **Where the two differ,** validation refuses. Its finding names both versions, and points to the capability's migration tier ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)).
- **No migration runs by itself.** Adopter data is often edited by hand, and a silent transformation is the wrong default.

## `pkit data validate <path>`

`pkit data validate` checks adopter data files against the schemas their bindings name. It takes one file, or a folder, whose YAML files it walks recursively.

- **What it runs:** the binding, then JSON Schema validation of each file against the schema bound to it, then the reference pass below.
- **Its exit:** non-zero on any binding that does not resolve, and on any finding that fails.
- **Beside `pkit schemas validate`:** that command validates the schema pairs in both homes, this area (`.pkit/schemas/`) and each installed capability's `schemas/`. This command validates the adopter's data against those schemas.
- **An answer file named to it** is judged against the answer files' schema, which its folder binds it to ([COR-062](../decisions/core/COR-062-answers-in-own-files.md) point 2). It reaches no binding.
- **Within `pkit validate`:** its `data` member runs both passes on every file of the repository that a `pkit_schema:` field or a `binds_to:` glob claims. A file nothing claims is no adopter data there, and no finding.

The CLI reference's `data validate` gives the command's output and what its walk leaves out ([its section](../cli/README.md#data-validate-path)).

## Cross-file references in adopter data: `x-pkit-reference-namespace` (COR-029)

Adopter data files name each other's entries ([COR-029](../decisions/core/COR-029-adopter-data-references.md)). A `[<namespace>:<id>]` token in one bound file names an entry another bound file defines. For example, a trip's file cites `[transport:asiana-fux5mv]`, which that trip's transport file defines.

`pkit data validate` resolves these tokens in a second pass, after the shape pass. The pass runs by default, and `--shape-only` skips it.

Two things make these references differ from the references `pkit schemas validate` resolves between a capability's schemas:

- **A reference resolves through the binding, to the bound file.** A capability schema that describes adopter data keeps its own id collection empty by design, since the entries live in the adopter's tree. So the reference resolves into the files bound to its namespace. Each file's ids are read through the companion's `x-pkit-id-collection` pointer.
- **A reference is read only where a field says so.** Adopter data carries bracketed text that is no reference, such as prose. So the resolver reads only the fields that the citing schema's companion marks with `x-pkit-reference-namespace: "<namespace>"`.
  - **What the mark says:** this field holds references in that namespace. The token still carries its namespace itself.
  - **Its counterpart:** the mark is for a value, as `x-pkit-keys-from-namespace` is for a mapping's keys.
  - **Where it goes:** on a field holding one value, on an array's `items`, or on a shared `$defs` definition that other fields `$ref`:

  ```json
  "$defs": {
    "transport_ref": {
      "type": "string",
      "x-pkit-reference-namespace": "transport"
    }
  }
  ```

**The scope is what is validated.** A namespace's pool of ids is the union of every file in scope bound to that namespace. In scope means under the folder that `pkit data validate` was pointed at. In `pkit validate`'s `data` member, the scope is every bound file of the repository.

- **Isolation comes from what is validated.** Validate one instance's folder, and only its data is in scope. Validate a parent folder, and a shared file under it serves every instance below.
- **A file's place within the scope changes nothing.** A reference never resolves by position, and no file shadows another, since the pool is a union.

**What fails:**

- **A value at a marked field that is no `[<namespace>:<id>]` token** is an error.
- **A token in another namespace than the field's mark declares** is an error.
- **A dangling id** is an error: the namespace has a pool in scope, and the id is not in it.
- **A duplicate id** across the files of one namespace in scope is an error, since the pool is ambiguous.
- **A namespace whose companion declares no `x-pkit-id-collection`,** or cannot be read, is an error: the reference cannot be resolved.
- **A namespace with no bound file in scope** gives a warning, and fails nothing. Data written step by step often names a sibling file that does not exist yet.

**Not decided yet:** a shared root of references that serves several instances without joining them into one scope, and mapping keys that name another file's entries. Each waits for a later record, once a real consumer needs it (COR-029).

## Authoring

The `schema` skill covers schemas that describe adopter data, through its `author.md` and `extend.md` sub-procedures. It is one composite skill ([COR-020](../decisions/core/COR-020-skill-folder-form.md)).

- **The stamp.** `pkit new schema <owner> <name>` stamps a pair into its owner's home. `<owner>` is a capability's name, or `core`, which stamps into this area, `.pkit/schemas/`. The other schemas verbs, `schemas validate`, `list`, `show`, `add` and `rename`, treat `core` as an owner beside every capability.
- **A schema of adopter data** adds the `binds_to:` field to its YAML, beside the namespace's content.
- **The adopter's files** carry the `pkit_schema:` field and the editor's directive, as recommended above.
