---
id: DEC-045
title: Named per-user instances — a local topology that references workstreams, with guided assignment and clone provisioning
status: accepted
date: 2026-07-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** [project-management:DEC-035-instance-ownership] tells one person's
concurrent clones apart by an *interchangeable number*. In practice a person runs
clones with *distinct jobs* — a "data" clone, a "map" clone — and wants each clone to
know its own name and role, and to route backlog work to the right clone. This record
adds, opt-in and on top of DEC-035: a **human-readable name** per clone; a **per-user,
machine-local topology file** (not committed, not team-shared) that lists the person's
instances and, for each, the **workstreams it handles**; a **guided script** that walks
the person through distributing their workstreams across their instances; and a
**`create-instance` provisioning script** that clones the repo into a sibling folder
and scaffolds its config. Instances **reference** workstreams — they never rewrite the
workstream taxonomy — and the whole layer stays a pm-side routing aid that never enters
the engine.

## Context

DEC-035 is deliberately flat and fungible: clones are interchangeable numeric peers,
and its clash tie-break ("lowest number wins") is justified by *"which of one person's
clones wins is immaterial."* That is the right floor. But the lived usage that prompted
this record is not fungible — a person runs, e.g., `trip-planner-agent` (main),
`…-data`, `…-poi-data`, `…-app`, `…-map`, each a clone focused on a slice of the
project. Two needs follow that DEC-035 does not serve: each clone should be **self-aware
of its name and role**, and the person should be able to **route work** so the data
clone picks up data work rather than any clone grabbing anything.

The design space was walked with two reviewers and several early framings were dropped:

- A **team-shared committed registry with a privileged `main` writer** was rejected. It
  reversed DEC-035's explicit "no committed registry" rationale, inserted a single point
  of failure and a spoofable client-side privilege, and — since a committed file is
  distributed by git — did not even deliver the "only main sees the whole topology"
  property it was meant to. The operator's own correction is the resolution: the topology
  is **per-user local configuration**, not team state.
- **Binding instance identity onto the workstream taxonomy** was rejected. Workstreams
  are long-lived *categorisation* ([project-management:DEC-018-workstream-taxonomy-and-lifecycle]);
  the parallelization work already refused to overload them as an operational partition
  ([project-management:DEC-025-parallelization-primitive] — "overloading them muddies the
  semantic; renames break the lock partition"). Writing "which clone" onto a workstream
  would repeat that mistake. The fix is to **reference, not rebind**.

This record is opt-in and additive: a person who sets no instance name gets exactly
DEC-035 (or the flat, single-clone no-op). It builds on the ownership marker
DEC-035 defines and [project-management:DEC-043-ownership-substrate-selection] made
substrate-selectable; it does not change how ownership is *marked*, only how the
*expected* owner is *derived* for the guard.

## Decision

**Add an opt-in named-instance layer, held entirely in per-user-local configuration,
that references workstreams to route work — on top of DEC-035, changing none of its
marking or clash mechanics.**

**1. Instances gain a human-readable name.** `set-instance`
([project-management:DEC-035-instance-ownership] point 1) is extended so a clone's
git-ignored, clone-local runtime identity carries a **display name** (e.g. `data`,
`map`, `main`) alongside the numeric id. The name is a self-awareness affordance and a
routing key; the numeric id and the `(assignee, instance:N)` owner from DEC-035 are
unchanged underneath.

**2. A per-user, machine-local topology file — not committed, not team-shared.** The
person declares their instances in a **user-local file** (resolved from a per-user
location, not the repo tree, and never committed). For each named instance it lists the
**workstream slugs that instance handles** and, optionally, path hints. Because the
file is per-user, it *is* the whole-topology view for that person's clones — any of
their clones reads it — so there is **no privileged `main` clone and no coordinator**:
`main` is just a conventional name for the person's primary clone, carrying no special
authority. A different team member runs their own clones with their own local topology;
the two never share this file. This keeps DEC-035's "each person's instances are their
own, coordinated with no committed registry" property intact.

**3. Instances reference workstreams (1:many); they never rebind the taxonomy.** An
instance handles a *set* of workstreams, and the reference lives only in the user-local
topology file — **nothing writes instance identity onto a workstream label, and
workstream is not made an instance attribute** (DEC-018's taxonomy and DEC-012's axis
model are untouched). The reference is a routing hint, not a fourth classification axis.

**4. The partition is soft — full coverage is the default, sharing and gaps are allowed
but discouraged.** The guided assignment (point 6) drives toward every workstream
handled by exactly one instance. A workstream handled by **two or more** instances
(shared) or by **none** (unassigned) is **permitted but surfaced at
`[validation-severity:warning]`** per [project-management:DEC-014-validation-severity-model]
— flagged, never hard-blocked.

**5. Ownership derivation feeds the pm-layer guard only, and degrades gracefully.** For
an issue in workstream *W*, the *expected* owner is the instance(s) whose topology
references *W*:
- **exactly one** → the DEC-035 clash guard warns if a *different* instance claims it;
- **several** (shared *W*) → any of them is fine, no warning;
- **none** (unassigned *W*, or an issue with no workstream) → there is no derived
  expectation, so the guard **falls back to DEC-035's flat numeric commons behaviour**.

The *expected* owner is derived from the per-user topology file (point 2); the *actual*
current owner is resolved separately through the ownership seam ([pkit:ADR-041]). The
clash guard consumes **both** — comparing actual against expected — and, with listings,
is the **only** consumer; **never** a gate, a transition, or the cascade fold.
Realm-blindness (DEC-035 point 8, DEC-043 D6) is preserved: naming instances does
not make ownership engine state. The named layer thus *refines* DEC-035 where the
reference is unambiguous and *falls back* to it otherwise — the numeric model stays the
floor.

**6. A guided assignment script — local, idempotent, drift-reconciling.** A script walks
the person through distributing their workstreams across their instances and writes the
user-local topology file. It runs against the person's own local config (no membership
gate, no privileged clone — it is local configuration). It is **re-runnable**: on each
run it reconciles **drift against the workstream lifecycle** (DEC-018 add / merge /
split / remove) — surfacing newly-unassigned workstreams and references to
now-removed workstreams or deleted instances (all at `warning`) and walking the person
through fixing them, rather than assuming a clean slate.

**7. A `create-instance` provisioning script.** A script clones the repo into a sibling
folder with a name-derived suffix and scaffolds the new clone's config (its
`set-instance` name + topology entry). It **confirms before any filesystem mutation**
(creating or removing a clone directory is destructive-adjacent per `.pkit/rules/core.md`
rule 8) and wires the new clone up with the project's pkit setup so it behaves like any
other clone. It provisions clones for the person running it, on their own machine — it
does not mutate any other repository's context (`.pkit/rules/core.md` rule 18).

**8. Deferred, named-not-built (per [pkit:COR-007]).** The *automatic* "decompose this
project into instances for me" step — proposing which instances should exist and where
the boundaries fall — is **not** built here. That decision blends pm routing with
*architectural* component-boundary judgment (the `architect`'s discipline per
[pkit:COR-026]); when built it should be a `project-manager` sub-procedure (the
[project-management:DEC-029-project-manager-agent-shape] batch-plan pattern) that
*consults* the architect for boundaries, **not** a new agent. Also deferred: any
team-shared topology. This record ships only the *mechanical* guided assignment (point 6)
the person drives, and gates the automatic decomposition on lived evidence from using it.

## Rationale

**Why per-user-local, not a committed team registry.** The motivating unit is *one
person's set of clones*, which is exactly DEC-035's unit ("each person's instances are
their own"). Holding the topology in per-user-local config keeps DEC-035's no-committed-
registry property, removes the single-point-of-failure and spoofable-privilege problems
a shared registry + `main` writer introduced, and needs no coordination protocol — the
person's clones all read one local file. A team-shared topology is a different, larger
concern with its own concurrency and authority questions; it is deferred until there is
evidence it is wanted.

**Why reference workstreams instead of a new partition axis or rebinding them.** The
person already thinks in domain areas, and those are workstreams — so referencing them
is the least-surprising routing key and avoids inventing a third overlapping partition
(DEC-018 workstreams, DEC-025 lanes, and now instances). But *rebinding* — writing
instance identity onto workstreams — is the overload DEC-025 already rejected: it would
make one label mean both "what kind of work" and "which worker", and couple categorisation
churn (rename/merge) to the work-split. A one-way reference held in the local topology
file gets the routing benefit with none of the coupling; the workstream taxonomy never
learns that instances exist.

**Why soft partition at `warning`.** "Allow but discourage" is exactly a
[project-management:DEC-014-validation-severity-model] `warning`: the clean full-coverage
partition is the guided default, and the flexible cases (a shared area during a busy
week, a freshly-created unassigned workstream) proceed with a flag rather than a wall.
The derivation degrades to match — shared means any owner is fine, unassigned falls back
to DEC-035 — so permitting the soft cases never leaves the guard in an undefined state;
it either warns, allows, or falls back to the numeric floor.

**Why keep the automatic decomposition out.** Deciding *how* to carve a project into
instances is component-boundary judgment, which is architectural, and building it now —
from a single example topology, on top of a DEC-035 that is itself not yet
implemented — is generality ahead of evidence ([pkit:COR-007]; DEC-035 itself invoked
COR-007 to refuse speculative instance generality). The mechanical assignment a person
drives earns its keep immediately (a colleague adopting the kit cannot hand-manage it);
the automatic version waits for lived use of the mechanical one.

### Alternatives considered

- **Committed team-shared registry with a privileged `main` writer.** Rejected — reverses
  DEC-035's no-committed-registry rationale, adds a single point of failure and a spoofable
  privilege, and a committed file is distributed anyway so `main`-only-view is illusory.
  Per-user-local delivers the whole-topology view with none of it.
- **Rebind / overload workstreams as the instance partition.** Rejected — the exact
  overload DEC-025 refused (categorisation ≠ operational partition; renames/merges break
  the split). Reference, one-way, from local config instead.
- **A new fourth classification axis for instances.** Rejected — ownership is explicitly
  not a classification axis (DEC-035 point 2); a routing reference in local config is not
  axis material and must not distort DEC-012.
- **Strict partition (hard-block shared/unassigned).** Rejected — too rigid for real
  weeks; `warning` with graceful derivation degradation covers the soft cases without an
  undefined guard state.
- **Build the automatic project-decomposition planner now.** Deferred — architectural
  boundary judgment (COR-026) from one example on an unbuilt base; COR-007 says wait for
  evidence and, when built, make it a `project-manager` sub-procedure consulting the
  architect, not a new agent.
- **Fold provisioning into a separate ADR-gated record.** Considered (a reviewer flagged
  the filesystem/session-boundary surface); kept in this record as per-user pm tooling
  with the rule-8 confirmation and rule-18 own-repo-only constraints stated. If provisioning
  grows beyond clone-plus-scaffold, split it out then.

## Implications

- **`set-instance` gains a name** alongside the numeric id in the clone-local runtime
  file (DEC-035 point 1); additive, still git-ignored, still opt-in.
- **A per-user-local topology file** (resolved from a per-user home/config location
  *outside* any repo tree, so it is shared across the person's clones and never
  committed — distinct from DEC-035's in-repo git-ignored clone-local id) lists the
  person's named instances and the workstream slugs each references, with optional path
  hints. A new schema describes it; it is **not** `substrate-map.yaml` and **not** a
  committed project registry like `workstreams.yaml` / `members.yaml`.
- **The ownership clash guard computes the *expected* owner from the workstream→instance
  reference in the per-user topology file** and compares it against the *actual* owner
  resolved through the ADR-041 seam (singleton warns / shared allows / unassigned falls
  back to DEC-035 numeric commons). Consumed by the pm-layer guard and listings only; the
  engine and cascade fold never read it (DEC-035 point 8 / DEC-043 D6).
- **Two new scripts:** the **guided assignment** (local, idempotent, reconciles DEC-018
  workstream-lifecycle drift, surfaces shared/unassigned at `warning`) and
  **`create-instance`** (clone into a sibling folder + scaffold config; rule-8 confirm
  before filesystem mutation; rule-18 own-machine only; wires pkit setup for the new clone).
- **DEC-035 gains a reciprocal refinement note** — instances may carry a name and
  reference workstreams for routing; the flat numeric model, the ownership marker, and the
  clash mechanics are unchanged and remain the fallback. **This record refines accepted
  foundational DEC-035, so promotion `proposed → accepted` requires explicit maintainer
  sign-off**, the same class as DEC-035's handoff-contract sign-off and DEC-043's DEC-035
  refinement.
- **No new mesh interaction** ([project-management:DEC-022-methodology-mesh]) — the
  topology is per-user-local operational state, repo-local by nature; `check-mesh` ignores
  it, the same stance DEC-025 takes for lanes. State this so a future author does not wire
  it into the mesh.
- **Surface change** (name in `set-instance`, new local topology schema, two scripts,
  guard-derivation change) → capability version bump per [pkit:PRJ-002]. No migration for
  existing adopters: the layer is opt-in and its state is per-user-local, so a repo with
  no topology file behaves exactly as DEC-035 (or flat).
- **Deferred, named-not-built:** the automatic project-decomposition planner (a future
  `project-manager` sub-procedure consulting the `architect`, gated on lived evidence per
  COR-007) and any team-shared topology.
