---
authors:
  - Ales Kalfas <kalfas.ales@gmail.com>
started: 2026-05-22
---

# Modular install surface — what `.pkit/` should contain, what should live at project root, and how components depend on each other

## The question

Four interrelated concerns, raised in the conversation that produced issue #112 (capability-command dispatch) and #113 (project-management pre-check):

1. **Source vs installed conflation.** project-kit self-hosts: `.pkit/` is both the source-of-edit for the methodology AND the consumed adopter content. The conflation breaks testability — the source repo can't exercise the adopter experience (install, uninstall, upgrade) without endangering the source. `pkit init` already refuses on the source for this reason; `pkit install capability` doesn't refuse but fails by collision (see the "What I got wrong earlier" thread in conversation).

2. **Bare-minimum install + opt-in adoption.** Today `pkit init` propagates a fixed bundle of areas — `PROPAGATED_AREAS = (decisions, workflow, skills, cli, adapters, scratchpad, agents, schemas)`. Every adopter gets all of them, regardless of whether they want them. Capabilities are opt-in; areas aren't. The line between "everyone needs this" and "some adopters need this" is fuzzier than the current binary suggests.

3. **Adopter content sunken inside `.pkit/`.** Some content the adopter authors lives deep inside the tooling folder — `.pkit/decisions/project/PRJ-NNN-*.md`, `.pkit/scratchpad/active/*.md`, future `.pkit/capabilities/<name>/project/config.yaml`. These are the *project's own* content, not infrastructure. The `.pkit/` prefix (with leading dot) signals "kit tooling, ignorable to most readers"; burying first-class project content underneath fights that signal.

4. **Capability dependencies.** Capabilities will increasingly compose. A future `compliance` capability would build on `evidence` (citations gate compliance claims); a `release-notes` capability would build on `project-management` (it reads issue/PR state). Today `package.yaml` carries no declared dependency on other components. The question: capability-specific dep mechanism, or a general one across all component types (capability, bundle, adapter)?

The four concerns are entangled — a modular install with multiple opt-in capabilities **needs** dependency declarations to function safely; adopter-content surfacing is informed by what gets installed in the first place. But the eventual crystallisations may be separate records, so they should stay separable in this note. The retirement event may produce multiple records; that's allowed.

## Forces

- **Adopter cognitive load.** A fresh adopter cloning a kit-adopting project should see at a glance "this is what the project authors maintain" vs "this is kit tooling that ships from upstream." Today, both live under `.pkit/` and the distinction is by sub-directory (`core/` vs `project/`). The signal-to-noise ratio for new readers is low.

- **Testability of the kit itself.** project-kit develops capabilities, areas, and adapters. Each needs exercising in adopter conditions before shipping. Today this requires either (a) a tmp-dir scratch adopter (used in tests; non-interactive), or (b) a separate real adopter project (heavyweight; gates the dev loop on having an external repo). A self-hosting project that can *also* be its own adopter would close this gap.

- **Composition pressure.** Issue #104 surfaced that the `project-management` capability already wants the `evidence` capability for the "no doc impact" claim discipline (every Shape B justification is essentially a claim that should be evidence-grounded; today it's free-form prose). As capability count grows, declared dependencies become load-bearing — install order, version compatibility, refusal-on-missing-dep, upgrade-cascade.

- **Backward compatibility.** Any restructure has to migrate existing adopters. Today's `.pkit/` layout is documented across COR records, the README, every skill's `reads.paths`, every cross-reference. A bulk migration is needed for any move.

- **The kit's own discipline of "ship working, refine in place"** ([COR-007]). Premature generalisation is the failure mode this note must avoid. The proposal should be motivated by concrete present pain (the four concerns above), not speculative future needs.

## What is already known

- **COR-001** establishes the cornerstone: kit-shipped content is source-of-truth from upstream; adopter-authored content lives in `project/` subdirectories. The split is by sub-directory within each area today.
- **COR-002** specifies the merge-primitive for fixed-path adopter files (e.g., `.claude/settings.json`); separate from the area-propagation mechanism.
- **COR-004** specifies install behaviour. `pkit init` refuses to re-run on already-initialised adopters and refuses to run on the source repo.
- **COR-005** + **COR-006** define the component pattern (bundles, adapters as siblings; capabilities added later in COR-017).
- **COR-011** establishes the area variants (universal vs specialised vs bundle-based). Different areas have different propagation rules.
- **COR-013** establishes the agent/skill reference graph — every reference declared and cited bidirectionally. Path moves break this graph; a restructure has to carry the moves through every record + artifact.
- **COR-017** establishes the capability pattern. Capabilities install/uninstall opt-in. The mechanism predates the current modularity question.
- **COR-018** establishes the schemas mechanism. Schemas live inside capabilities (per-capability `schemas/`) and area-level (the `.pkit/schemas/_defs/` library). Both layers propagate to adopters today.

## Candidate alternatives

### A. Status quo — accept the conflation

Don't restructure. Document the self-hosting limitation, recommend a separate adopter project for kit-level testing, accept that some adopter content lives at `.pkit/<area>/project/`. Lowest cost; doesn't address any of the four concerns.

**Pros**: zero migration cost; no breakage to existing adopters; the kit keeps shipping.
**Cons**: the testability hole stays. Dogfooding requires a separate project. Adopter content stays sunken. No path to declared dependencies.

### B. Source/installed separation only — `kit-source/` vs `.pkit/`

Move the canonical source for kit-shipped content (areas, capabilities, schemas/_defs/, cli, adapters) out of `.pkit/` into a new `kit-source/` directory at the repo root. `.pkit/` becomes purely the *installed/derived* state — empty by default; populated when the developer runs `pkit init` on the source repo (or `pkit install capability X` for a capability).

- `find_source_kit()` resolves to `<repo>/kit-source/` instead of `<repo>/.pkit/`.
- project-kit now BEHAVES like any other adopter: empty `.pkit/`, install capabilities into it for testing.
- The dev loop adds an explicit install step: edit `kit-source/...`, run `pkit sync` to refresh `.pkit/`, test.

**Pros**: closes the testability hole cleanly. Adopter experience and source experience are now the same shape. The conflation disappears.
**Cons**: massive migration. Every record, doc, skill's `reads.paths`, every cross-reference changes. `@.pkit/rules/core.md` in CLAUDE.md changes. Tests with hardcoded paths change. Possibly two or three PRs of mechanical movement work.

### C. Surface adopter content at project root

Move adopter-authored content out of `.pkit/<area>/project/` to top-level directories at project root:

- `.pkit/decisions/project/PRJ-NNN-*.md` → `decisions/PRJ-NNN-*.md`
- `.pkit/scratchpad/active/...` → `scratchpad/active/...`
- `.pkit/capabilities/<name>/project/config.yaml` → `<name>-config.yaml` (or a single `pkit.yaml`)

Kit-shipped content stays under `.pkit/`. The split becomes: `.pkit/` = tooling and upstream-managed content (read-only-ish for adopters); top-level dirs = the project's own authored content.

**Pros**: directly addresses the "sunken content" concern. Project-authored content is visible where readers look. Matches the convention of other tooling (`.git/` vs working tree; `node_modules/` vs `package.json`).
**Cons**: also a large migration. Every cross-reference between PRJ records and CORs changes. The split between "kit-managed" and "project-authored" is harder to maintain on an area-by-area basis (some areas have both shipped and project content tightly interleaved). The convention of `.pkit/<area>/{core,project}/` was COR-011's deliberate design; moving away from it is a meaningful reversal.

### D. Bare-minimum install + opt-in area adoption

Replace `PROPAGATED_AREAS` (the fixed list everyone gets) with a per-adopter opt-in:

- Core minimum: `cli/`, `manifest.yaml`, possibly `decisions/` (every adopter needs PRJ-NNN somewhere).
- Optional areas: `scratchpad/`, `workflow/` (with bundle selection), `agents/`, `skills/`, `schemas/`, etc.
- Capabilities: already opt-in (status quo).
- Init is interactive: prompts for which areas the adopter wants, or accepts a profile flag (`pkit init --profile minimal | standard | full`).

**Pros**: clean opt-in model; adopters who don't use scratchpads don't see scratchpad infrastructure; adopters with their own workflow tooling don't get the github-issues bundle baked in. Matches the capability discipline at the area level.
**Cons**: harder to reason about which adopter has what. Cross-references between records assume areas exist (a COR-013 mention of `.pkit/agents/README.md` doesn't resolve if the adopter didn't install agents). Either every record carries a "requires area X" declaration, or some areas are *effectively* universal even if technically opt-in. May produce more confusion than it solves.

### E. General component-dependency mechanism

Independent of A-D: extend `package.yaml` across all component types (bundle, adapter, capability) with a `dependencies:` block:

```yaml
schema_version: 1
component:
  kind: capability
  name: compliance
  version: 0.1.0
description: Compliance discipline ...
requires_backbone: ">=1.24.0,<2.0.0"
dependencies:
  capabilities:
    - name: evidence
      version: ">=0.2.0,<1.0.0"
  bundles: []
  adapters: []
```

Install refuses on missing deps with an actionable hint ("install `evidence` first"). Uninstall refuses to remove a dep if a dependent is still installed (or cascade-uninstalls with confirmation). Upgrades resolve compatible versions across the dependency graph.

**Pros**: well-trodden ground (npm/cargo/pip have solved this for decades). Makes capability composition real. Per-component-type — capabilities depend on capabilities most commonly, but the mechanism generalises.
**Cons**: dependency resolution adds complexity to the install path. Version-range parsing already exists for `requires_backbone`; reusing the parser keeps cost down. Premature without a second capability that wants composition — but project-management ↔ evidence is the second case already (the "no doc impact" justification flow benefits from evidence).

### F. Combinations

The four concerns can be addressed in different combinations:

- **B + E** — source/installed separation + dependency declarations. Closes the testability hole AND the composition gap, but doesn't address adopter-content visibility (C) or area opt-in (D).
- **C + E** — surface adopter content + dependency declarations. Addresses visibility and composition, leaves source/installed conflation.
- **B + C + E** — the most thorough restructure. Higher migration cost but resolves three of the four concerns.
- **All of A–E** — including D (opt-in areas) is the maximal change. Probably overshoots.

## Open questions

- **Which content is "kit-shipped" vs "adopter-authored"?** The current `core/` vs `project/` split inside each area is one answer. Is that split right? Are there per-area exceptions (e.g., `scratchpad` is entirely project-authored; the kit ships only the README and convention)?
- **What's the smallest set of changes that closes the testability hole?** If B alone fixes testability without C or D, that's the smallest win. C and D are independent improvements that could come later.
- **For dependencies (E): is the dep graph cyclic-safe?** Probably yes (capabilities are leaf-ish and don't cycle by construction), but the mechanism should be explicit about cycle detection at install time.
- **For dependencies (E): what about `evidence`'s relationship to `project-management`?** Specifically: should the project-management capability's `## Doc impact` Shape B justification be required to cite evidence? Today it's prose. If evidence becomes a dep, every adopter installing project-management gets evidence — which fixes the "the no-doc-impact claim is just a vibe-check" problem but force-couples two capabilities that some adopters might want independently.
- **Naming for the source directory** (B). `kit-source/` is one option; `source/`, `src/.pkit-source/`, `pkit-source/`, `methodology/` (pm-workflow uses this) are others. Should match the kit's existing prose conventions.
- **For C: does adopter content at root play nicely with sub-projects in monorepos?** Most adopters are single-project; the kit's no-shared-files invariant assumes one `.pkit/` per project tree. Surfacing `decisions/` at root could collide with sub-project decisions; needs thought.
- **What does this mean for sync?** `pkit sync` re-propagates kit-shipped content. With B, sync refreshes `.pkit/` from `kit-source/` — straightforward. With D (opt-in areas), sync skips areas the adopter didn't install — does it still detect newly-shipped areas and offer adoption? Probably yes (opt-in defaults to "ask on first sync after upstream introduces the area").

## What this note explicitly excludes

- **Capability-command CLI dispatch** — covered by issue #112. Independent of this note's restructure question.
- **The pre-check script for project-management** — covered by issue #113. Independent.
- **The four stacked PRs against #104** — those land first; this restructure work is downstream of them.
- **Specific COR-NNN numbering for the records that crystallise** — assigned at authoring time, after this note's exploration settles.

## Next steps for this exploration

1. Walk through the cross-references that would break under B (every `@.pkit/rules/core.md` include, every `reads.paths` declaration mentioning `.pkit/`, every COR cross-reference to `.pkit/<area>/README.md`). Estimate the migration surface concretely.
2. Sketch the `dependencies:` block schema (E) and validate it against the two concrete cases — `compliance` requires `evidence`; `release-notes` requires `project-management`.
3. Test the C proposal on the current adopter content — list every file under `.pkit/<area>/project/` and decide whether each genuinely benefits from surfacing.
4. If after 1–3 the proposal still holds, draft the implementing CORs (likely two: one for the layout restructure covering A–C/D, one for component dependencies covering E).
