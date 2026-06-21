---
id: COR-031
title: A capability has an origin — kit-shipped or incubated-in-repo
status: accepted
date: 2026-06-20
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

A capability can be born in two places: shipped by the methodology and copied into a project on install (the case COR-017 assumes), or **authored and kept in the adopting project's own repo** (incubated). This record makes that distinction — a capability's *origin* — explicit, so a project can run a capability it wrote itself as a first-class capability, and so the kit's sync operation leaves that home-grown capability alone instead of trying to refresh it from a source that does not exist.

The practical payoff: an adopter can build and use a discipline locally *before* (or instead of) it ever graduates into the methodology, without scattering the work across project-owned files and without the kit's sync clobbering it.

## Context

[COR-017](COR-017-capability-pattern.md) introduced the capability as the kit's opt-in packaging primitive, but it described only one way a capability comes into being: the kit ships it, and install *copies the subtree from kit source* into the adopter's `.pkit/capabilities/<name>/`. The whole install / sync / upgrade lifecycle in COR-017 assumes that copy-from-source origin — sync "auto-upgrades installed capabilities" by re-copying from the kit, and a capability the kit no longer ships is treated as an anomaly to warn about.

That assumption breaks for a capability an adopter authors in its *own* repo. Two real cases ground this: a project building a domain discipline it may later contribute upstream, and a project carrying a capability that is permanently local. In both, the adopter's working tree *is* the source of truth — there is no upstream to copy from or reconcile against. Registered the same way a kit-shipped capability is, such a capability is a hazard: sync's reconciliation has no signal that the content is adopter-owned, so it misclassifies it as kit content gone missing — flagging it "no longer shipped" or, worse, attempting a refresh from an empty source that destroys adopter-authored work. The deeper principle at stake is the no-shared-files invariant ([COR-001](COR-001-content-mechanisms.md)): an incubated capability's files are adopter-owned and must never become sync-managed. The lifecycle cannot honour that boundary without knowing where the capability came from.

The lifecycle, in other words, needs to know *where a capability came from* before it can decide what `sync` / `upgrade` / `validate` may do to it. That property is missing today.

## Decision

A capability has an **origin** — a first-class property recorded at registration that tells the lifecycle how the capability relates to the kit source. Two origins are defined now:

- **`kit-shipped`** — the capability is shipped by the methodology and entered the project by being copied from the kit source on install. This is the status quo COR-017 describes; it remains the default.
- **`incubated-in-repo`** — the capability was authored in, and lives in, the adopting project's own repository. It is **adopter-owned content** (project tier per COR-001), not a copy of anything the kit ships.

The following rules apply:

**D1 — The lifecycle excludes incubated capabilities from source-reconciliation, but not from self-consistency checks.** The kit's sync / upgrade operations must *skip* an `incubated-in-repo` capability when reconciling installed content against the kit source — there is no source to reconcile against, and the files are adopter-owned. This suppresses *reconciliation against the kit source only*. It does **not** suppress structural self-consistency validation: an incubated capability's own manifest, schemas, and citations are still worth checking against the adopter's working tree, since that tree is its spec. The capability is also honoured for every other purpose: dependency gating ([COR-030](COR-030-capability-dependencies.md)) counts it as installed, and the harness deploy primitives ([COR-013](COR-013-agent-architecture.md)) deploy its skills and agents exactly as for a kit-shipped capability. Origin governs *source-reconciliation only*, not participation or self-validation.

**D2 — Origin is recorded in lifecycle-owned install-state, defaulting to `kit-shipped`.** The act that records a capability as installed also records its origin — and it records it in the project's lifecycle-owned install registry (the install-state that already tracks which capabilities are present), **not** inside the capability's own subtree. This placement is load-bearing: an incubated capability's subtree — including its authored manifest — is entirely adopter-owned, so writing lifecycle state into it would re-create the very ownership blur this record exists to prevent. An install-state entry that carries no origin is read as `kit-shipped`, so existing registered capabilities keep their current behaviour with no re-tagging. The change is purely additive (an optional field with a safe default — the same additive shape COR-030 used for its dependency field, requiring no migration).

**D3 — Registering an incubated capability does not copy.** For a kit-shipped capability, entering the project means copying the subtree from kit source. For an incubated capability the subtree is *already in place* — source and destination are the same directory — so registration records and activates (deploys skills/agents, registers for dependency gating) but performs no copy.

**D4 — Every lifecycle verb honours origin; removal never destroys adopter-owned source.** Origin-awareness is not limited to sync — *any* verb that resolves a capability against the kit source or rewrites its files must branch on origin. Two consequences are load-bearing:

- **Uninstall of an incubated capability unregisters it in place.** It removes the install-state entry and re-runs deploy to drop stale harness symlinks, but **leaves the adopter's authored subtree on disk** — that subtree is the only copy of the work, and deleting it is the exact destroy-adopter-work hazard this record exists to prevent. Deleting an incubated capability's files, if ever wanted, is a separate explicit opt-in, never the default. (Uninstall of a `kit-shipped` capability still deletes its subtree — there it is a disposable copy of kit source.)
- **Upgrade of an incubated capability does not resolve against the kit source.** There is none; "upgrade" re-applies deploy from the in-repo tree. It must never be reported as a no-longer-shipped orphan or steer the adopter toward a destructive removal.

Two further origins are **anticipated but deferred** until a concrete need arises, per the pattern-extraction discipline ([COR-007](COR-007-pattern-extraction.md)): a capability sourced from outside the kit (e.g. a private repository or local path), and the *transition* of an incubated capability into kit-shipped status (graduation). Neither has a grounded consumer today; naming them here reserves the shape without specifying mechanism.

### Boundary cases

Three cases sit near the origin line and are resolved as follows:

- **A kit-shipped capability the adopter edits in place** stays `kit-shipped`. Local edits do not flip origin; they are reconciled away on the next sync exactly as the no-shared-files invariant already prescribes. Incubation is about *authorship origin*, not *local divergence*.
- **An incubated capability whose name later collides with a newly kit-shipped one** is graduation arriving unbidden (the deferred case showing up early). Until graduation is specified, the lifecycle must *surface the collision* (the adopter now has a same-named kit capability available) rather than silently skip it — so the adopter can decide. The default skip applies only while no kit capability of that name exists.
- **A dependency edge with one incubated end** behaves identically to an all-kit-shipped edge: dependency resolution reads the declared range from the manifest regardless of origin. Origin does not gate the edge in either direction.

## Rationale

**Why origin is a property, not two unrelated lifecycles.** The alternative is to treat an in-repo capability as something entirely separate from a capability — a different concept with its own commands and rules. Rejected: nearly everything about a capability is identical regardless of where it was born (its layout, its manifest, its dependency edges, how its skills deploy). Only one thing differs — whether the kit source is authoritative for its content. Modelling that single difference as an *origin* property keeps one capability concept and one lifecycle, with a single decision point (source-reconciliation: yes/no) keyed off origin. This is the smallest change that closes the gap.

**Why sync must skip rather than warn.** COR-017 already has a "no-longer-shipped" warning for a kit-shipped capability whose source vanished. Reusing that path for incubated capabilities would be wrong twice over: it mislabels a deliberately-local capability as a missing one, and it invites a refresh that would overwrite adopter work. The skip is not a degraded mode — it is the correct semantics for adopter-owned content under the no-shared-files invariant, which says sync never touches project-owned paths.

**Why default to `kit-shipped` and stay additive.** Forcing every already-registered capability to be re-tagged would be an adopter-breaking change requiring a migration ([COR-010](COR-010-resource-lifecycle.md)). Defaulting an absent origin to `kit-shipped` preserves today's behaviour exactly for every existing install, so the feature lands as a pure addition. Cheap, safe, reversible.

**Why defer external sources and graduation.** Both are real and anticipated, but neither has a consumer yet: incubation has grounded cases, sources and promotion do not. Specifying their mechanics now would be speculative generality — the exact failure the pattern-extraction discipline guards against. Reserving the names without the machinery lets the axis grow when a second need actually appears.

### Alternatives considered

- **A separate "local capability" concept distinct from a capability.** Rejected — duplicates the entire capability model to express a one-bit difference (is the kit source authoritative?). An origin property is the minimal expression.
- **Let sync treat in-repo capabilities as kit-shipped and rely on the existing "no-longer-shipped" warning.** Rejected — mislabels deliberate local content as missing and risks overwriting adopter work on refresh.
- **Require a migration to tag existing capabilities with an origin.** Rejected — an absent origin can safely mean `kit-shipped`, making the change additive and migration-free.
- **Derive origin from kit-source presence instead of recording it.** At reconciliation, treat a registered capability the kit currently ships as `kit-shipped` and one it does not as adopter-owned — storing nothing. Rejected: derivation misfires whenever a capability is *temporarily* absent from kit source (mid-refactor, a renamed-but-not-yet-resynced kit), silently reclassifying kit content as adopter-owned; and it cannot express the deferred external-source origin, which is neither "in kit source" nor "in repo." A recorded property is stable across kit-source churn and extensible to the deferred origins. (The `absent ⇒ kit-shipped` default is a one-time read of legacy state, not ongoing derivation.)
- **Specify external sources and promotion now, as part of the same axis.** Rejected per COR-007 — no grounded consumer; defer until one appears.

## Implications

- **Refines COR-017.** The capability lifecycle now branches on origin: install-by-copy and source-reconciliation apply to `kit-shipped` capabilities; `incubated-in-repo` capabilities are registered-in-place and excluded from reconciliation. COR-017 gains a one-line forward pointer to this record. The project's lifecycle-owned install-state grows an optional origin marker (absent ⇒ `kit-shipped`); the capability's own authored manifest is unchanged.
- **Refines COR-010.** The reconciliation order that sync / upgrade follow gains a skip-branch for adopter-owned (incubated) components, while self-consistency validation still applies. This is the lifecycle hook that makes the no-shared-files invariant hold for in-repo capabilities.
- **Composes with COR-030 and COR-013 unchanged.** An incubated capability participates in dependency resolution and harness deploy identically to a kit-shipped one; origin does not gate those.
- **No migration.** Per D2 the change is additive (absent origin ⇒ `kit-shipped`); no adopter state is renamed or removed. The CLI surface that records origin and activates an in-repo capability, and the exact install-state field that stores it, are operational detail owned by the CLI and capability-schema reference docs — not enumerated here.
- **Implementing work.** With this record accepted, its forward-pointer refinements to COR-017 and COR-010 land alongside it. The install-state origin field, the no-copy register path, and the sync skip-branch are authored under the capability-incubation feature, not here.
- **Deferred work.** External capability sources and incubated→kit-shipped graduation are reserved as future origins/transitions; each earns its own decision when a consumer exists.
