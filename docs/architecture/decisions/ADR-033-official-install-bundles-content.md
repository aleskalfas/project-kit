---
id: ADR-033
title: Official install bundles methodology content, version-locked to the binary
status: accepted
date: 2026-06-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The official adopter install (`uv tool install git+ssh://…project-kit.git`, per PRJ-004)
**cannot actually set up or upgrade an adopter project** — `init`/`sync`/`upgrade` all fail
from the installed binary. That directly contradicts what PRJ-004 and the CLI README promise
(the binary "works against any adopting project", listing `init`/`sync`). Issue #333 under
EPIC #332.

The cause: the built wheel ships only the Python package (`src/project_kit`) plus the VERSION
file — it does **not** carry the `.pkit/` methodology tree (decisions, schemas, skills,
agents, adapters, capabilities, migrations). `find_source_kit()` resolves the propagation
source by walking the filesystem relative to the installed package (`<pkg>/../../.pkit`), so
inside a `uv tool` venv it points at a path that does not exist — `init` raises a clean guard
error, while `upgrade`/`sync` crash with a raw `FileNotFoundError`. The scratchpad note
`.pkit/scratchpad/active/2026-06-26-pkit-install-versioning-model.md` works the design space
and identifies the root cause and the two-version-axes drift problem (binary version vs the
adopter's `.pkit/VERSION`).

## Decision

The official install **resolves methodology content from package data bundled in the wheel,
version-locked to the binary.** `find_source_kit()` prefers a real checkout when present and
falls back to the bundled content otherwise. Concretely:

### 1. Bundle the propagation surface, not the whole `.pkit/` tree

The wheel bundles *exactly what `pkit sync` propagates*, under the package path
`project_kit/_kit/`. The rule — not the list — is what this decides: the existing core/project
ownership boundary determines what's in. By that rule the bundle **excludes** adopter-owned
subtrees (for example `*/project/` such as `decisions/project/`, the maintainer's
`scratchpad/{active,done,dropped}` notes and `manifest.yaml`, and `.gitignore` / `__pycache__`
— illustrative of the rule's reach, not an authoritative list). Defining the bundle as the
propagation surface means it can
never drift from what sync copies.

### 2. Checkout-first resolution is a contract

`find_source_kit()` returns a real checkout's `.pkit/` when `(.pkit/"decisions").is_dir()`
holds; otherwise it returns the bundled `project_kit/_kit/`, resolved via
`importlib.resources`. The bundle is a *fallback*, never consulted when a real checkout is
present, and is resolved so it can never be mistaken for a checkout `.pkit/`.

### 3. Capability source is a distribution medium, not an activation surface

All shipped capabilities' source travels in the wheel (the "repository"); `capabilities
install <name>` remains on-demand into the adopter (COR-017's opt-in boundary unchanged —
the existing available-in-source vs installed split).

### 4. Migrations and capabilities must reach adopters

This fixes a pre-existing omission: `migrations/` and `capabilities/` are read from the
source kit but are absent from the propagation set, so backbone migrations have never reached
a non-self-host adopter and could not run.

## Rationale

**Why version-locking is the feature, not a side effect.** The scratchpad's failure-mode
analysis shows the wedging hazard is a pinned binary running against mismatched `.pkit/`
content. When the binary carries its own content, "binary version" and "the content it syncs"
are identical by construction — one of the two drift axes collapses for the official install.
That is the load-bearing reason to bundle the content over the alternatives below.

**Why bundle-as-propagation-surface beats bundle-the-tree.** Framing the bundle as "what sync
propagates" makes the PRJ-record exclusion, the manifest exclusion, and the scratchpad
exclusion all fall out of one existing ownership rule, and guarantees the wheel cannot drift
from what sync actually copies. A blanket "copy `.pkit/`" rule would sweep adopter-owned and
maintainer-only artifacts into adopters.

**Why the mechanism is packaging-agnostic (and therefore final, not interim).** "Bundle
content as package data + resolve via `importlib.resources`" is identical whether pkit is
delivered by git URL (today), a registry, or frozen into a standalone binary. Only the
delivery wrapper changes up the distribution ladder; the resolution mechanism does not. So
this is the durable foundation, not a throwaway step.

### Alternatives considered

- **Fetch source at sync/upgrade time** from the pinned git ref. Rejected — reintroduces
  network access and auth at upgrade time, and keeps content separate from the binary
  (preserving the drift axis this decision collapses).
- **Concede the gap** — revise PRJ-004 + README to declare the tool install operational-only,
  keep a checkout as the sanctioned propagation path. Rejected — leaves the golden path
  broken (B4–B6), forces adopters to clone, and contradicts the install-experience goal.

## Implications

- **Clarifies (does not supersede) PRJ-004.** PRJ-004's decision (direct git URL, no
  registry) is untouched; bundling is fully compatible with it. What changes is PRJ-004's
  imprecise *implication* that the wheel ships only the package. A one-line forward-pointer
  is added to PRJ-004 referencing this ADR.
- **CLI README correction.** The "works against any adopting project" claim becomes true once
  bundled; the README is updated to describe what the official install can do (closes
  scratchpad item B10).
- **Migration framework (COR-010) unchanged in contract, fixed in coverage.** The tier model
  holds; package-data-vs-checkout only changes where `find_source_kit()` points. The
  `migrations/` propagation omission is fixed in the same change (per `rules/core.md` #7,
  which presumes migrations reach adopters).
- **COR-007 follow-on (flagged, not forced here).** Two hand-maintained lists must agree —
  the wheel's force-include and the propagator's area set. The robust design is a single
  declaration of the kit-owned tree consumed by both build and propagator; the
  `capabilities`/`migrations` omissions are the recurrence evidence. Recorded as a follow-on,
  not built in this change.
- **Wheel size** grows (all methodology content + capability source ship in `site-packages`),
  acceptable at current scale; revisit if a future capability bundles large binary assets.
- **Surface change** → version bump per PRJ-002, and the migration-coverage check runs against
  the propagation-set change.
- **Self-host coherence preserved.** In a project-kit checkout the real `.pkit/` wins
  (checkout-first), so self-host detection and dev live-edit are unaffected; the bundled
  `_kit/` is only consulted in adopter venvs, where self-host is never true.
