---
id: ADR-056
title: Backbone file schemas live under the schemas area, bind by location rule, and are read from the tree
status: accepted
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the backbone now validates four kinds of file it does not write — the configuration file, rule-set files, the project files that answer a data point, and the methodology's block in an artefact's front matter. The core records say those schemas exist, are strict, and how their versions work. This record fixes project-kit's realisation: the schemas are propagated files under `.pkit/schemas/backbone/`; each finds its files by *where they are*, in a fixed order; the binary reads the tree's copy; and one renderer produces every "unknown key, did you mean …" message.

## Context

The schemas mechanism was built for kit-shipped data — a capability's `<name>.yaml` with its companion, and adopter data bound to it through a `pkit_schema:` field or a `binds_to:` glob ([COR-023](../../../.pkit/decisions/core/COR-023-schema-binds-inline.md), superseding [COR-022](../../../.pkit/decisions/core/COR-022-schema-data-binding.md)). The new class — the schemas README calls them *backbone file schemas* — fits none of that: the backbone ships only the shape, the instance is someone else's file, and none carries a capability's schema name.

The contract is in core. The configuration record makes the file strict and says its schema ships with the backbone ([COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 4). The friction record fixes the block's shape by a backbone schema applied strictly ([COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) point 2). The slots record has the filler envelope carry its schema version ([COR-052](../../../.pkit/decisions/core/COR-052-slots.md) points 2 and 5). The connection-points record defines the container, how validation tells a functionality block from a role block from a typo, and that backbone-owned blocks carry no version ([COR-053](../../../.pkit/decisions/core/COR-053-connection-points.md) point 10), leaving the filler path mapping to the reference and placement to "the project's architecture decisions". This record is that decision.

## Decision

1. **Home: propagated, one copy, under `.pkit/schemas/backbone/`.** Schemas are propagated data in this distribution (the permission core's decision data, the process shape contract — [ADR-003](ADR-003-permission-core-code-home.md), [ADR-020](ADR-020-process-engine-placement.md) Implications), and these are schemas. Two reasons make the tree the *right* copy rather than merely a permitted one: the configuration file's shape is the one the installed backbone defines, and the installed backbone is the tree (COR-048 point 6); and an editor reading a `$schema` directive is a consumer that cannot reach the binary. The binary reads the tree's files and carries none of its own. A tree that lacks a schema for a kind — one recorded before that schema landed — skips that kind and reports "no schema present, skipped", never validates against a shape the tree never shipped. The directive is stamped only where an editor can use it: the configuration file and filler files, which are plain YAML.

2. **Binding by location rule, in this order.** A file is claimed by the first rule that matches; a claimed file never reaches the capability-data resolution of COR-023.
   - **Fixed path** — the configuration file at the path the CLI reference documents (COR-048 point 1).
   - **Filler path** — the path derived from a point address under the backbone-owned sub-path beneath the internal documentation root (COR-052 point 2). The mapping from `<publisher>::<role>:<point>` to a path is **injective on valid addresses**, so that no two points share a file and no path binds the wrong schema; the reference shows the mapping and its inverse.
   - **Rule-set file** — a collection file in a place declared to hold rule sets (COR-051 point 2). Its entries also carry the container, so the container rule applies inside it.
   - **Container** — the front matter of a Markdown document, or a collection entry, in a declared place (COR-050 point 1). A plain YAML data file in a declared place is not a document: it falls through to COR-023.

   Consequences stated so nobody discovers them: `pkit data validate` delegates a location-claimed path to this pass rather than refusing it for lack of a binding; a capability whose `binds_to:` glob would match a claimed path is a capability defect, not an ambiguity; a filler whose point has no active provider has its envelope validated and its body left alone, reported as inert (COR-052 point 2).

3. **Versions, as the records place them.** The filler envelope and each point block inside a role block carry `schema_version`, the companion integer of the point (COR-052 point 5, COR-053 point 10). Backbone-owned shapes — the configuration file, the friction block, the rule-set file's shape — carry no version: they change through migrations ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)), and a version key in the configuration file would be a key only a core record may own (COR-048 point 2). One invariant binds any migration of the friction block: it preserves the parsed value of `at`, or every revalidation point in the repository moves (COR-050 point 3).

4. **One renderer.** Every unknown-key finding across the class comes from one module: the offending key, the nearest known key by edit distance, and — for the container — the reminder that a role block needs a versioned point block. The known set for the container is the shipped functionality names, the active role words and their qualified forms (COR-053 point 10). Reading posture is not unified here and stays with each owning record: configuration readers warn and use the default (COR-048 point 4); the friction checks never skip an unparsable artefact (COR-050 point 2).

5. **Run by `pkit validate`.** The pass is a registered validator of the umbrella command the configuration record names (COR-048 point 4); `pkit data validate` and `pkit schemas validate` remain as focused surfaces and are registered members of the same umbrella.

## Rationale

**Why the tree, not the binary.** The shape of the configuration file is a property of the *installed* methodology, and the installed methodology is the tree. A binary newer than the tree validating against its own copy would report keys the adopter cannot yet write. The editor consumer is real for the two plain-YAML kinds and costs nothing for the rest.

**Why location, not a field.** The `pkit_schema:` field exists so a reader can tell which of many capability schemas a data file follows (COR-023). These files have no such ambiguity: one path, one derived path, one declared place, one container key — and the container has nowhere to put a field. A field would restate what the location already fixes.

**Why a fixed order of rules.** A rule-set file is a collection whose entries carry the container; without an order, two rules claim one file and the report is doubled or contradictory. Ordering by specificity — an exact path, a derived path, a declared file kind, a declared place — gives one claim per file.

**Why one renderer.** Four schemas producing four phrasings of the same finding would teach people four things; a misspelt key in the configuration file and a misspelt block in an artefact are the same mistake and should read the same.

**Why an ADR and not a COR or a PRJ.** The core records decide that the schemas exist, are strict, how they version and how the container is read; they leave placement and the path mapping to this distribution. Where the shipped files live, the order the resolver consults, and the shape of the renderer are project-kit's realisation — the altitude of ADR-020 — not principles binding every methodology, and not project workflow ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)).

### Alternatives considered

- **Ship the schemas inside the binary only.** Rejected: the tree defines the configuration file's shape, and the editor cannot reach the binary.
- **Ship both a binary copy and a propagated copy.** Rejected: two copies drift; nothing needs the second.
- **Put them in `_defs/`, with the process shape contract.** Rejected: `_defs/` is the shared `$defs` library that every schema registry loads for every validation; four root schemas nobody `$ref`s would ride along everywhere under a misleading name.
- **Put them as direct children of `.pkit/schemas/`.** Rejected: the pair walk enumerates YAML halves and derives companions, so a lone companion would be invisible to it and never checked as a schema.
- **Bind through `pkit_schema:` in each file, or `binds_to:` globs on the schemas.** Rejected: no ambiguity to resolve, and no room for a field in the container.
- **A version key in the configuration file or the friction block.** Rejected by the core records (COR-048 point 2, COR-053 point 10); restated here only because the question recurs.

## Implications

- **Four companion-only schemas land under `.pkit/schemas/backbone/`**: the configuration file, the container (document and collection-entry forms, with the friction block), the rule-set file, and the filler envelope. Adding them is additive to the propagation surface — a changeset ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)), no migration. The schemas pass gains a load-check of that directory so a malformed schema there is caught.
- **Each core record that adds a key or field extends the matching schema in the same change-set** (COR-048 Implications); an incompatible change to a backbone-owned shape ships a migration that rewrites the instances (COR-010), preserving the friction block's `at`.
- **`pkit validate` gains the pass and the shared renderer** as one module the pass and any later schema of this class use.
- **The schemas README is the reference** for the class and the container; the CLI reference is to document the location rules and the address-to-path mapping when the resolver lands.
- **Authoring commands that create a configuration file or a filler file stamp the editor directive** at the propagated schema path.
- **Recorded trigger to revisit.** If a reading path ever needs one of these schemas where the tree is unavailable — a hook running outside a checkout — the binary would need its own copy, and the one-copy rule of point 1 is reopened with drift handling decided then.
