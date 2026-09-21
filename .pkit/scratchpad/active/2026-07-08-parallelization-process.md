---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-07-08
---

# Parallelization process — a staged, contract-first workflow over the parallelization primitive

Sibling to [`2026-05-26-parallelization-primitive`](2026-05-26-parallelization-primitive.md).
That note explores the **substrate** (lanes + typed `Blocked by:` + ready-frontier) and
crystallises into [project-management:DEC-025-parallelization-primitive] (currently `proposed`).
**This** note explores the *layer above* — a **staged process** that makes parallelism
conflict-free *by construction*, and crystallises into a **new** project-management "parallelization
process" DEC. The split follows the skill's own boundary test: two distinct crystallisation events
(promote DEC-025; author the process DEC), so two sibling notes.

**Provenance.** Inbound from a second adopter, `trip-planner-agent`, whose source note is
`…/trip-planner-agent/.pkit/scratchpad/active/2026-07-08-parallelization-process.md`. That adopter
runs **four clones of one repo against one tracker** (`main` / `poi-data` / `data` / `app`) and
wants to go to **two instances per workstream, split by layer** — the lived multi-instance evidence
DEC-025 was parked waiting for. This note is the kit-side design carrier; the DEC(s) crystallise
here.

## The question

Can "run as many meaningful parallel instances as possible, without unnecessary conflicts" be a
**single, unified, staged process** — the parallelization analogue of the staged processes other
capabilities ship — rather than improvised per split? And what is the machine-readable **map** such
a process operates on to compute "what is safe to start now"?

## Forces

- **Conflict-free parallelism is the goal, not just more instances.** Naive fan-out produces merge
  collisions and step-on-each-other; the win is preventing conflicts, not merely catching them.
- **The split is always by layer/component.** A workstream decomposes into architectural layers,
  each an arm. The cut is where both the leverage and the risk live.
- **Contract-first is the conflict-*preventer*.** The operator's key insight: author the *seam*
  (interfaces, schemas, `_lib` helpers, signatures) **before** fanning out; once frozen, the arms
  are genuinely independent. Lanes/locks (DEC-025) only *catch* what leaks; a frozen contract means
  the arms rarely touch the same files at all.
- **Dependencies must be precise and queryable**, not prose — an orchestrator computing the ready
  frontier cannot parse narrative.
- **A contract change mid-flight is an event**, not silent drift — it must re-freeze the seam and
  propagate to the dependent arms.
- **Don't over-gate ([COR-007]).** A one-file change must not trigger a parallelization ceremony;
  the process scales with the size of the split.
- **Kit-owned.** Primitive + process live in the project-management capability; implementation is
  upstream (here). This project supplies the design; the adopters supply the lived evidence.

## What is already known / related

- **[project-management:DEC-025-parallelization-primitive]** (`proposed`) — the *substrate* this
  process rides on: separates **code-surface conflict** (overlapping files → `lane:<slug>` locks,
  one in-flight issue per lane) from **sequence conflict** (B needs A's outcome → typed
  `Blocked by: #N`), plus a **ready-frontier reporter**. Landed `proposed` on purpose, pending lived
  evidence; the sibling primitive note is its carrier. The trip-planner run is the **second**
  adopter's evidence (after IGW), which is the recurrence [COR-007] wants before promotion.
- **[project-management:DEC-018-workstream-taxonomy-and-lifecycle]** — workstreams are *long-lived
  domain categorisation*; DEC-025 deliberately refused to overload them as lock partitions. So there
  are **three orthogonal partitions**: **workstream** (domain), **lane** (code-area lock), and
  **instance** (who is working it). This process composes all three.
- **[project-management:DEC-005-linking-and-containment]** — the prose `## Dependencies` section
  DEC-025's typed `Blocked by:` refines into a parseable graph.
- **Instance ownership** — [project-management:DEC-035-instance-ownership] (built), refined by
  [project-management:DEC-043-ownership-substrate-selection] and
  [project-management:DEC-045-named-per-user-instances] (decided; the named/topology layer is the
  in-flight EPIC #508 program, partly built — `set-instance` + the seam landed; claim/guard/listing
  wiring #519–#521 open).
- **The staged-process pattern.** The `software-engineering` capability is building a staged,
  gated workflow (its producer/conventions seam is [software-engineering:DEC-001-producer-agent-and-conventions-seam];
  the per-increment ladder is developing). The recurring shape across such processes is a
  **connector** — a handoff artifact between stages/disciplines. A parallelization process is that
  idea generalised: a **contract/handoff artifact between parallel arms** rather than between
  disciplines. *(Note: the trip-planner source note cites `software-engineering:DEC-002/003` and a
  `ux-ui-design` process; those record ids do not resolve in this repo — treated here as the
  external pattern, not cited as kit records, per axiom discipline.)*

## The model (brainstormed)

A **process** layered on DEC-025's **primitive**. DEC-025 supplies the lock (lanes) and the
sequence graph (typed `Blocked by:`); this process supplies the **staged workflow + the
contract-first freeze step** that make parallelism conflict-free by construction.

The two conflict types are DEC-025's; the staged workflow is the new part:

1. **Cut** — decompose the body of work into arms by layer/component; name the lanes.
2. **Author + freeze the contract** — a *single-instance, pre-parallel, reviewed* step: build the
   seam (interfaces, schemas, `_lib` helpers, signatures) the arms will share; **freeze** it. The
   conflict-*preventer*, and the analogue of a stage connector.
3. **Fan out** — assign each arm a `lane` + an `instance`; arms build against the frozen contract
   independently. *Two instances per workstream = two instances each holding a different lane in
   that workstream.* Workstream = domain; lane = layer/lock; instance = worker — the three compose.
4. **Sequence** — typed `Blocked by:` between arms; the ready-frontier reporter surfaces the
   unblocked set for pickup.
5. **Integrate + propagate** — arms merge; a **contract change mid-flight is its own event** that
   re-freezes the seam and propagates (re-sync, not silent drift) to the dependent arms.

**Cross-workstream is the same shape at a larger grain** — a contract *between workstreams* is this
process with workstreams as the arms.

## The dependency/architecture map — derived, dynamic

The process operates on a **machine-readable map**: compute the ready frontier, turn a cycle into a
sequence, know which contract a change propagates to, see which lane/layer is free. Two disciplines:

- **Derived, never stored.** The map is *projected on demand* from artifacts pkit already holds —
  issues + typed `Blocked by:` (dep edges), decisions + cross-refs (the decision graph), schemas
  (contracts/seams), workstreams + lanes (partitions), layer tags. Never a hand-maintained parallel
  file that drifts from what it describes. (The adopter grounds this in its own derive-don't-store
  decisions.)
- **An apparent cycle is runtime sequencing, not a code cycle** — resolved as an ordering the graph
  computes (typed `Blocked by:` for a pass), not a design knot.

**Ops ladder ([COR-007] — crystallise each rung from lived evidence, not up front):**
1. **frontier** — "what's safe to start now" (already DEC-025's reporter over the Blocked-by graph). Usable first.
2. **cycle-as-sequencing** — detect a dependency cycle, surface it as an ordering to resolve.
3. **contract-awareness** — tag which schema/seam is a contract; show what a change propagates to.
4. **layer-aware parallelization** — project the **workstream × lane × instance** view: "what can
   these N instances safely pick up right now."

## The contract-freeze mechanism (resolved — reuses existing primitives)

No new "contract artifact" type; the freeze is built from issues + Blocked-by + the review gate +
schema versioning + the audit-log facility.

- **The contract is a Task**; its deliverable *is* the shared seam (schemas, `_lib` signatures,
  interfaces). **Frozen = its PR merges** (WIP while open, frozen once landed on `main`) — the PR
  lifecycle, not a new flag. Grounding example: `connectors.schema.json` + `_lib/extractions.py`
  landed *first*, then the arms built on them.
- **Fan-out rides the dependency graph.** Each arm carries `Blocked by: #<contract-task>`; the
  ready-frontier reporter surfaces no arm until the contract Task closes. Contract-first is enforced
  by the Blocked-by graph, not a separate gate.
- **A mid-flight change = a new contract Task (v2) that re-blocks the consuming arms** (`Blocked by:
  #<contract-v2>`), dropping them off the frontier until they rebase (the re-sync); logged through
  [project-management:DEC-044-audit-log-facility]. Versioning rides on the seam itself — a schema
  seam bumps `schema_version` (+ migration, [project-management:DEC-017]); a `_lib` seam is git
  history + the Task. **Propagation is derived** — the contract Task's Blocked-by fan-out edges *are*
  the "what does this change touch" graph (map-ladder rung 3, for free).
- **Freeze sign-off = the review gate + a required `architect`** (a contract is a cross-cutting
  seam) — the conditional-reviewer trigger [project-management:DEC-032], mirroring
  review-before-kickoff in the staged processes.
- **Cut threshold ([COR-007] over-gate guard): ≥2 arms sharing a seam** fires the ceremony; one arm
  or no shared surface → do it serially.
- **Contract identification: explicit marker + derived propagation.** A Task is marked a `contract`
  intentionally (via the comment-log substrate, same as lanes) so the architect-sign-off requirement
  can fire *before* fan-out; the propagation graph stays derived from the Blocked-by edges. (Pure-
  derived can't gate a *pre*-fan-out freeze — a Task only "becomes" a contract once arms already
  point at it, too late to gate.)

## Engine operations the process must provide (emphasised requirement)

All three operate on the **derived** graph and reconcile it onto the substrate spine (comment-log
source of truth → description mirror → label reflection where creatable). They are the operational
surface the eventual tooling ships:

1. **Reconcile (idempotent whole-graph update).** Recompute the derived graph (lanes, Blocked-by,
   contract edges, frontier) from the comment-log source of truth and **update the whole set of
   tasks** — refresh each issue's description mirror and reconcile its `lane:*` / marker labels to
   match. **Idempotent**: re-running on an in-sync graph is a no-op; a partial/interrupted run
   recovers by re-running (per-issue value-equality, the [project-management:DEC-037] discipline).
2. **Introspect (drift report).** Compare the **derived model** (from the comment-log truth) against
   the **state reflected on the tasks** (descriptions + labels) and surface the delta — a `status`
   for the parallelization graph. Read-only; pairs with reconcile (introspect shows drift, reconcile
   heals it). Never mutates.
3. **Disable / teardown.** Turn the functionality off on a repo and **remove all remnants** — lane
   markers, contract markers, derived description-mirror regions, and `lane:*` labels. The teardown
   is itself **logged as a comment event** (a terminal record on the audit log), then reflected by
   refreshing descriptions (mirror region removed) and reconciling labels (removed). Even removal
   follows comment → description → label; nothing is deleted label-first, so the disable is clean and
   auditable and a re-enable can read the history.

These reinforce **derive-don't-store**: the tasks' descriptions/labels are always a *projection* of
the comment-log truth, so reconcile/introspect/disable are all "recompute the projection" operations
over the one source.

## Open questions (for the crystallised process DEC)

New to the process layer (the primitive's own open questions live in the sibling note):

- **Where does the contract live, and how is it "frozen"/versioned?** Tagged commit? Schema version?
  A dedicated contract artifact? How is a frozen contract distinguished from work-in-progress?
- **How is a contract *change* propagated?** A typed `Blocked by:` variant ("re-sync against
  contract vN")? A broadcast event? Who re-freezes?
- **Granularity of the cut** — when is a split worth the contract ceremony vs doing it serially
  (the COR-007 over-gate guard)? A size/independence threshold.
- **How the three partitions compose** — workstream × lane × instance. Is "two instances per
  workstream, split by lane" expressible, and does DEC-045's workstream→instance routing need a
  **lane dimension** (instance handles *workstream × lane*)? **Deferred** — that extension depends
  on the half-built instance-ownership program (EPIC #508); keep it out of the process DEC's
  critical path and revisit once #519–#521 land.
- **Who signs off the frozen contract** — the `architect` (cross-cutting seams)? A reviewer gate
  before fan-out, mirroring the staged processes' review-before-kickoff?
- **One DEC or two?** Promote DEC-025 (primitive) *and* author a sibling process DEC, or fold the
  process into DEC-025's promotion? Working answer: **two** — the primitive and the process are
  distinct crystallisations (this sibling-note split mirrors that), and DEC-025 can promote on the
  substrate evidence alone while the process DEC carries the staged workflow.

## Session refinements — 2026-08-03 (for the architect pass; supersede earlier framing where they conflict)

A critic pass + a long design session reshaped the model. Captured here so the next pass resumes
from the current state, not the original sketch.

**Descope (from the critic pass).**
- The **primitive (DEC-025) cannot flip as a one-line accept**: its own promotion criterion is
  logged field-notes of real collisions — that section is still empty (we reasoned from hypotheticals
  + a second adopter that *intends* to scale). And the label-first → comment-log substrate switch
  **rewrites DEC-025's Decision section** and inherits the maintainer-sign-off class ADR-041 required.
- The **process DEC is premature**: one aspirational adopter, zero actual process runs; and its
  central novelty — "contract v2 re-blocks the arms" — is **broken as described** (a `Blocked by:`
  edge gates *pickup from the frontier*, not an arm a clone is *already working*). Contract-first may
  be a **doc/skill** (usage playbook), not a DEC (COR-006).
- **Plan:** ship **rung-1 tooling** (typed `Blocked by:` + ready-frontier reporter) to *generate*
  real field-notes; promote DEC-025 and decide the process's carrier only on that evidence.

**Occupancy is instance ownership, not a lane-lock.**
- The conflict that actually bites is **same-ticket occupancy**, not file-overlap. That is the
  DEC-035 claim + guard, whose override/reclaim (`--bypass` / `handoff --to-instance self`) is the
  operator's `--force` retake. **Lane-as-code-surface-lock is deferred** ([COR-007]) until file
  collisions actually recur — which dissolves the critic's "silent green-when-red under-declaration"
  hole (there is no file-lock left to under-declare).

**Deterministic routing model.**
- A ticket carries an **`area`** (its location in the decomposition: `app/backend`, `trip-data/data`,
  `trip-planning`). An instance declares a **`scope`** = the set of areas it covers. Routing =
  `ticket.area ∈ instance.scope`, computed by each instance from **its own scope alone** (no global
  knowledge). Occupancy (the claim) arbitrates when **>1 instance shares an area** — routing hands
  off to the claim exactly at the scale-out threshold. A **straddler** (a ticket whose area spans two
  scopes) surfaces as *ambiguous routing* — the visible signal that a seam wasn't frozen → contract-first.

**Nomenclature (defined).**
- **`area`** (on a ticket) — a node in the decomposition; the routing key.
- **`scope`** (on an instance) — the areas it covers. *Renamed from `owns`* to stop colliding with
  "ownership" (the per-ticket claim, DEC-035): an instance has a *scope*, and it *claims* tickets.
- **`discipline`** (on the **area**, not the instance) — the capability governing *how* work in that
  area is done (`software-engineering`, `ux-ui-design`, `authoring`). *Relocated from `process`*: it
  is intrinsic to the work, so an instance **inherits** disciplines from its scoped areas. The
  per-user file then carries only `scope`.

**Architecture vs topology — two layers.**
- **Architecture** (shared, one per project): areas + per-area discipline + **boundaries/contracts**.
- **Topology** (per-gh-user): which of *my* instances cover which areas (`scope`). References the
  architecture's areas.

**Boundaries = contracts between areas.**
- A boundary is drawn as the artifacts pkit already treats as contracts: a **schema** (`schema_version`),
  an **ADR** pinning an interface (like ADR-041), or a **`_lib` module's frozen signatures**. A
  **contract Task** is the *freeze/change event* on a boundary; the boundary artifact is its
  deliverable. The derived architecture map = **nodes: areas, edges: these contracts**.

**Topology storage — per-gh-user, location selectable.**
- One file **per GitHub user**, either **uncommitted-local** (`~/.pkit-home/<repo>/topology/<user>.yaml`,
  the throwaway-trial mode) or **committed** (`.pkit/.../topology/<user>.yaml`, persisted + team-visible).
  Per-user either way ⇒ no cross-user contention; removes the `runner:` field (filename = the user).
  Mesh-default / commit-optional applied to the topology.

**Shared issue-metadata substrate (the extraction — for the architect).**
- Lane/area metadata on tickets uses the shared substrate (comment-log → description mirror → label
  reflection where creatable). For **uncontended declarations** (area, blocked-by), GitHub-native
  edit/timeline history *is* the audit trail — so they do **not** need ownership's concurrency
  machinery (the critic's R3, reconciled: shared **carrier**, per-consumer **fold**). There are
  already **five** metadata-on-issue mechanisms (DEC-041 provenance, DEC-044 audit-log, DEC-024 hook
  stamps, ADR-041 ownership, DEC-039 children) → a strong recurrence to extract ONE shared
  "persist structured metadata on an issue" substrate.

**Topology lifecycle (the breaking points).** greenfield = no file; the file is **born at the first
split**; `discipline` **binds lazily**; `main` **narrows** as instances spawn; **routing → occupancy
handoff** at >1 instance per area; **local → committed** at the team boundary; **teardown** contracts
cleanly. Each transition = *edit one file + reconcile*.

**Engine operations (required).** idempotent whole-graph **reconcile**; read-only **introspect**
(drift: derived model vs reflected tasks); **disable/teardown** (removal logged through
comment → description → label). All are "recompute the projection over the source" — derive-don't-store.

**Next — the architect pass owes:** (a) the shared issue-metadata substrate extraction; (b) the
architecture-vs-topology split + boundaries-as-contracts (the derived map's contract); (c) the
**zero-commit adoption mode** — pkit config resolving from *outside* `.pkit/` so a repo can be tried
with nothing committed (a pkit-*core* question, bigger than lanes); (d) DEC vs doc/skill for the
process layer.

## Crystallisation target (this note's exit)

1. **Promote [project-management:DEC-025-parallelization-primitive] to `accepted`** — answer its
   evidence-shaped open questions from the two adopters' lived runs (feed the trip-planner evidence
   into the sibling primitive note's `## Field notes` / promotion criterion).
2. **Author a new project-management DEC** — the staged parallelization process + the contract-first
   freeze step, modelled on the staged-process/connector pattern.
3. **Build the tooling** — the ready-frontier reporter + `project/lanes.yaml` + `lane:<slug>` labels
   + typed `Blocked by:` parsing (ops-ladder rung 1), COR-007-gated for the higher rungs.

Retires (`pkit scratchpad done parallelization-process --produced …`) when the process DEC + the
first tooling rung land. The sibling primitive note retires on DEC-025's promotion.
