---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-21
---

# Process primitive

The pkit-side design canvas for a shared **process-structure primitive** — owns the core decision/mechanism that the upstream adopter briefs were handed up for. Co-designed with the user, one decision at a time; decisions are recorded here as they lock.

## The question

What is the shape of a reusable mechanism for *staged, guided, gated* processes that grow incrementally — designed up front as an abstract core, but grounded against real instances (not speculative)?

Owns: **EPIC #127** ("Generalise the workflow state machine into a shared process-structure primitive").

## Sources absorbed (don't re-derive)

- `trip-planner-agent-app/.pkit/scratchpad/active/2026-06-19-process-structure-primitive.md` — the primary brief (incl. the 2026-06-21 "system of branches" refinement). The adopter-legal carrier handed to pkit.
- `trip-planner-agent/.pkit/scratchpad/active/2026-06-21-trip-planning-as-a-process.md` — a fully-worked concrete instance to validate the engine against.
- pm `schemas/workflow.yaml` — the shipped reference shape.
- `project-kit/.pkit/scratchpad/active/2026-06-20-documents-registry-and-onboarding.md` — the living-docs *data* half (documents registry + onboarding/bootstrap meta-pattern); living-docs *adoption* is a grounding instance for this primitive.

## Grounding instances (COR-007 — richly satisfied)

1. **pm issue lifecycle** — shipped state machine (`workflow.yaml`).
2. **ux-ui-design design-maturity** — hand-rolled (`design-stages.yaml` + `scripts/`); the grounding reference for the single-branch layer.
3. **trip-planning** — fully worked (frame → derive → discover ⇄ deepen → enrich → render → plan).
4. **living-docs adoption** — the new driver; bootstrap (brownfield/greenfield) → … → keep-up-to-date (terminal).

Designing the core up front is grounded, not speculative — four real instances.

## LOCKED decisions

### D0 — Vocabulary: one substrate, two altitudes (2026-06-21)

One mechanism applied at two altitudes; the substrate is the background abstraction under both.

| Layer | Label | What it is | Instance | Priority |
|---|---|---|---|---|
| Substrate | **state machine** | states + guarded transitions + position; content-free | the engine | core |
| Altitude 1 — depth (single branch) | **process** | substrate bound to one discipline's journey over its units (+ subject, actor-per-move, gate criteria, hooks, invariants) | living-docs adoption; design-maturity; trip-planning; pm issue-lifecycle | 1 |
| Altitude 2 — breadth (system) | **workflow** | the graph of interacting processes (overflow edges, cross-branch gates); pm-as-tracker overlay | the project as a whole | 2 |

Same substrate at both altitudes — intra-unit moves and inter-branch moves are both "guarded transition" (the notes' depth-vs-breadth, different topologies). Naming nit deferred: pm's `workflow.yaml` is, under this scheme, a **process** definition; its tracker role is the workflow altitude.

### D1 — State-tracking model: subject + position + detection (2026-06-21)

The engine tracks the **process position** of a **subject**. A process declares **subject cardinality** — *singleton* (one journey, e.g. living-docs adoption) or *keyed* (many, e.g. one per screen/POI/issue). Each **state** declares how membership is **detected**: `inferred` (a predicate over reality/domain state), `stored` (the engine owns a position record), or `hybrid` (inferred with a stored override). "Memory" is then uniform: *resolve a subject's current state*.

Refinement: process **position** is kept *distinct from* the subject's **domain/lifecycle state** (e.g. a POI's `draft→verified`). `inferred` detection = *deriving position from* that domain state/reality.

### D2 (resolved 2026-06-21 → path C) — Thin substrate now; living-docs drives accretion

After critic review (RF-1 / RF-2 / the regret-risk), the "design the whole abstract core up front" scope is **rejected as COR-007-speculative**. Resolved to **path C**:

- Extract a deliberately **thin, content-free state-machine substrate** — states + guarded transitions + position + journal — and **rebind pm** onto it (proving it against the one *shipped* instance).
- Build **living-docs adoption concretely against the substrate** as the genuine *second shipped* instance.
- Richer process-layer features (D1 detection modes, D3 severity taxonomy, D5 hook failure-semantics, D4 invariants block, D-obs mandatory fields) **accrete only as a real binding demands them** — name-broad, ship-narrow (COR-016). They are now **hypotheses to confirm against the second binding**, not locked core.
- Breadth / altitude-2 (cascade, overflow, cross-branch gating) deferred; **budget the journal + cardinality + cascade migration when it lands** (RF-2), don't claim "no rework".

Accepted critic fixes to fold in when each feature is authored: **D3 cross-authority clause** (G-2); **live precheck authoritative over prose** (G-3); **definition-versioning** added to the queue (G-5); **vocabulary collision** (WR-1) to resolve before naming anything shipped.

### D3 — Anatomy of a guarded transition; gates must be checkable (2026-06-21)

A transition = `{from, to, trigger, authorisation, gate, severity, hooks}`. `authorisation` = *who* may move (`user` / `agent-autonomous` / `script`); `severity` = *how hard* the refusal (`hard-reject` / `bypassable-with-audit` / `warning`).

**The gate must reduce to something the engine can verify** — either a **deterministic predicate** it runs over the subject's artifact/domain-state, or a **recorded authorisation artifact** it confirms exists (sign-off token / audit comment / reviewer verdict, cf. pm `done-work` + DEC-028). Agent self-assertion ("I judged it done") is *never* sufficient on its own — a judgment gate must leave a checkable trace, or validation is theatre.

### D-obs — Observability / self-explainability is first-class, from the start (2026-06-21)

The engine is verbose, introspectable, and self-documenting so that (a) the AI uses it as parseable memory + validation, and (b) a human with no manual can see where we are, why, how we got here, and what's next. Three mechanisms:

1. **Self-describing definition (mandatory fields).** Each `state` carries `meaning`; each `transition` carries `why` + a human-readable `condition` description + a `hint` (next command). Load-bearing — the explain output renders from them.
2. **Per-subject journal (append-only).** Every move records `{ts, subject, from→to, trigger, actor, gate-result, severity, bypass+reason}` — the memory, the "how we got here", and the audit trail in one.
3. **`status` command — verbose, self-explaining by default.** Renders {definition + position + journal + **live gate-prechecks**}: where we are · why · how we got here · where we can go + conditions (with live pass/fail) + who + command hints + next suggestion. Two renderings: **narrative** (default, human) and `--json` (AI/machine). The precheck runs gates live so the explanation is true *now*.

### D4 — Cross-cutting invariants are first-class and position-independent (2026-06-21)

Two orthogonal kinds of check. A **transition gate** (D3) is edge-local ("may I make *this move*?"). An **invariant** is position-independent ("is the subject *valid right now*?") — checkable anytime, green at every committed boundary (cf. trip's `data validate`). The core ships the *mechanism*: an `invariants:` block, each `{condition (deterministic predicate), scope (always | [states]), severity, why}`, run by a generic `validate` command that reports self-explainingly (per D-obs). Disciplines declare their own invariants (trip: evidence-backed; living-docs: every doc registered with intent). A transition may fold "in-scope invariants hold" into its gate, but invariants exist independently.

### D5 — Hooks model: integral vs reactive; position never lies (2026-06-21)

A **hook** = an action a transition declares, firing on a legal move; it references a named action the *discipline* implements (open-branch, regenerate, validate, dispatch-reviewer), and every run is journaled. Two kinds by failure semantics, declared per-hook (default `integral`):

- **integral** — the hook *is the point* of the move; on failure the move is **refused/rolled back** (position unchanged). E.g. `start-work` must open the branch.
- **reactive** — a post-move side-effect; on failure it's **journaled as a warning** and surfaced by `status`, but position holds.

Invariant: "you are in state X" is always true — the engine never reports a half-applied move. **Breadth** (a move affecting *related* subjects — pm cascade / ux-ui journey-spawn) is the same family but **deferred per D2** (needs the second instance + workflow-altitude edges); shaped-toward, not built.

## Resolved (was the open queue)

All shape decisions resolved (D0–D6 + the determinism-spectrum and composition refinements). Remaining ◇ items are **named hypotheses that accrete per binding**, not open decisions. Next: author the foundational **COR**; then the pm-rebind DEC + the living-docs DEC (each cites the COR; pm's ships the COR-010 migration).

### D7 (resolved 2026-06-21) — predicate mechanism = capability-provided commands

How the content-free engine evaluates a capability's detection predicate / deterministic gate. Three candidates: (A) registered Python functions — rejected (engine would import capability code; breaks the content-free seam; capabilities ship PEP-723 scripts, not an importable package); (B) **capability-provided commands** — chosen; (C) declarative DSL — too weak alone (can't query live reality like "branch exists"/"PR merged", which is the point of inferred detection).

**Decision (B):** a predicate is `{ run: <command-name>, with: <args?> }` referencing a command the owning capability registers (the existing `scripts/` + `package.yaml` pattern). The engine resolves it in `<capability>` (from the definition's location), runs it with the subject + context, reads structured JSON:
- deterministic gate / detection: `{ result: bool, reason, detail? }` → engine uses `result`.
- authorisation-artifact gate: `{ exists: bool, produced_by: <authority>, reason, detail? }` → **the engine computes `result = exists && produced_by != actor`** (engine enforces cross-authority, not the capability).

`reason`/`detail` feed the status view's live precheck (self-explanation). Engine stays content-free; capabilities own predicate logic; fits the permission model; reality-queries work. Sharpens the pm rebind: pm's inference (branch-exists / pr-merged / checkboxes) becomes predicate commands the engine calls. Ship-narrow: command-refs only; a declarative-data convenience (the DSL, for trivial field checks) is named-deferred.

### D6 (resolved 2026-06-21) — blocked = derived detection (★) + first-class flag (◇)

Dissolve the binary (derived status vs new state). The engine **derives** "can I move?" live via gate-precheck (★ — `status`/`can-i-move` need it anyway); when blocked is a *wait*, it materialises a first-class **orthogonal runtime flag** (NOT a definition state → no state-space explosion): `blocked{blocked_on, resume_when, assignee?, since}`, journaled on enter/resume, with the engine re-evaluating `resume_when` live so `status` shows current readiness and the flag clears when satisfied. Gives the wait a journal entry + reason + duration + owner (critic CA-1 #1), a notify-on-enter / act-on-resume hook point (#2), and a typed `blocked_on` that distinguishes awaiting-human / awaiting-condition / awaiting-subprocess-outcome / deadlock (#3). Composition fit: a parent waiting on a subprocess is `blocked_on: <child outcome>`. Split: the derived "is there a legal move?" ships ★; the rich `blocked` record ships ◇ (when a binding needs rich human-in-the-loop).
- **D6 — human-in-the-loop**: a gate type, or a first-class pause/resume position?
- **D7 — loops as first-class**: "fix-the-stage-then-retest" + deepen loops — built-in or operator pattern?
- **D8 — engine/commands + binding**: the deterministic guide (where-am-I / can-I-move / move) — new script vs extend pm's `move-issue`; binding per COR-022/023.
- **D9 — generalise `workflow.yaml` in place vs new shared `process` schema + pm migration.**

## Critic review (2026-06-21)

Affirmed strengths: D3's "self-assertion never sufficient" principle (load-bearing, correct); the gate/invariant separation (D4); D-obs's live precheck; the substrate/content seam.

Challenges (to resolve or consciously accept + document):
- **RF-1 — D2 is COR-007-violating.** Only pm is *shipped*; ux-ui-design (hand-rolled prototype), trip-planning (post-hoc reading), living-docs (not built) confirm the *shape recurs* but not the *abstraction's shape*. Designing the variation axes (D1 detection modes, D3 severity, D5 integral/reactive, D-obs fields) before a second *binding* exists "locks in guesses." Honest framing: name-broad / ship-narrow — narrow ship = substrate + pm-rebind + one real new binding; richer features = hypotheses.
- **RF-2 — "no rework" (D2) is false.** pm (instance #1) already ships cascade, but D5 defers breadth → substrate can't express its own grounding instance; per-subject journal (D-obs) can't represent inter-subject events; D1 `keyed` drops pm's containment-tree structure. Downgrade to "minimise rework; budget the journal+cardinality+cascade migration."
- **G-2 — D3 forgeability.** A "recorded artifact" the *same* agent can write is theatre. Need a **cross-authority clause**: the artifact must be produced by a different authority than the one being gated (human / other agent / CI / external). (pm's merge button already satisfies this.)
- **G-3 — D-obs prose = the doc-rot we fight.** Mandatory `meaning`/`why`/`condition`-prose drift from predicates. Fix: derive prose from the predicate where possible; make the **live precheck authoritative** and prose explicitly subordinate.
- **G-4 — inferred state is not durable memory** (it's a recomputed view; reality shifts with no journal entry). The memory use-case forces `stored`/`hybrid` more than D1 admits.
- **G-5 — no definition-versioning decision** (definition changes under live subjects). The trip "fix-the-stage-then-retest" loop *is* this and recurred repeatedly. Add to queue.
- **WR-1 — vocabulary collides with the charter.** pm's artifact is named/documented as "workflow" everywhere; D0 reuses "workflow" for the system layer → two live meanings; EPIC #127's title reads backwards. Either rename pm's artifact (surface change + migration + doc sweep) or pick a third word for altitude-2.
- **WR-3 — `hybrid` under-specified** (override vs precheck read different truth sources).
- **CA-1 — D6 third option:** pause/resume as a first-class **orthogonal flag** (journaled, carries `blocked_on`/`resume_when`, doesn't multiply the state set) — dodges both "new state" and "derived status."
- **CA-2 — scope third option:** substrate-only-first (content-free substrate + rebind pm; richer features accrete as each new binding demands). Most COR-007-honest.
- **CA-3 — D9:** don't generalise `workflow.yaml` in place; new schema + pm migration keeps pm-specific bits (cascade / closure_triggers / pr_state_effect) out of the shared shape.
- **The one regret:** building the generic engine first will **stall the living-docs work the user actually wants**, which needs ~10% of the engine (a linear pipeline + a couple gates, mostly clone-existing-tooling). COR-007-faithful + unblocking move: do living-docs bespoke now → it becomes the genuine second shipped instance → extract the substrate from pm + living-docs (two shipped instances that actually disagree).

**Effect:** D2 is **reopened** pending the sequencing decision below. Next reviewer: `architect` (RF-2, G-1, CA-3 are architectural-custody).

## Architect review (2026-06-21)

Verdict: **path C is architecturally sound, not refused.** One escalation (placement), two firm recommendations (vocabulary, migration), a concrete thin/thick line.

**ESCALATION — schema placement (needs user sign-off; gates everything).** The kit has two tiers only: backbone vs capability/adapter. A shared cross-capability schema is, by dependency position, **backbone-owned** — a first (backbone has never owned a content-bearing schema; COR-023's `pkit_schema: <capability>:<schema>` grammar has no `<capability>` for it). Two options:
- **(A)** backbone owns a content-bearing `process` namespace schema → must grow COR-023's binding grammar.
- **(B)** backbone owns the process *shape contract* (a meta-schema + `_defs` fragments + the engine); **each capability ships its own instance schema conforming to it** → COR-023 untouched, capabilities stay self-describing peers. **← architect + I recommend B.**

**RESOLVED 2026-06-21 → B.** Three independent votes: COR-023 binding grammar untouched · capability independence (living-docs doesn't depend on pm to borrow a shape) · **composition needs each process self-contained *and* addressable by `<capability>:<process-id>`** — exactly what B provides. B *enables* the use-it-everywhere / compose-complex-structures substrate; A would route composition through one central namespace and add grammar.

Placement under B:
```
.pkit/schemas/_defs/process.schema.json   # shared $defs: state, transition, journal-entry, invariant shapes
.pkit/<process-area>/README.md            # engine spec + shape contract (backbone area, like lifecycle/)
.pkit/capabilities/project-management/schemas/workflow.yaml  # pm instance, declares conformance
.pkit/capabilities/<living-docs>/schemas/<stages>.yaml       # living-docs instance, same shape
```

**Vocabulary (resolves WR-1).** Do NOT rename pm's `workflow.yaml` (big blast radius for no shipped gain; it *is* a workflow in plain English). Instead give altitude-2 a non-colliding word: **state machine** (substrate) → **process** (altitude-1) → **orchestration** / **process-system** (altitude-2). Retitle EPIC #127 to drop the backwards "workflow" framing.

**pm-rebind real-proof test.** Substrate absorbs `states` + `transitions` + forks/self-loops. `cascade` / `closure_triggers` / `pr_state_effect` stay **pm-local, explicitly OUT** of the substrate. The rebind proves the seam iff the substrate-conformant part is a clean subset and pm extensions are clearly demarcated; if they can't cleanly separate, the seam is wrong — and learning that pre-ship is also a win. A rebind that doesn't force the separation is a no-op.

**Migration.** Capability-tier, `schema_version` 2→3, idempotent (detect via version), a value-preserving shape transform (override-safe). Budget the *second* (expensive) migration for when altitude-2 moves breadth into the substrate slot — name both in the COR; don't pretend "no rework".

**Thin/thick line (concrete).** Ship: states (id, `meaning`, `inferred_from`) + transitions (from, to, trigger, `authorisation`, `severity`) + forks/loops + position + append-only journal + self-explaining `status` (live precheck authoritative). All in **`singleton` + `inferred` mode only**. *Name but don't ship:* `keyed` cardinality (living-docs is a **singleton**; pm's keying is the containment tree = altitude-2, so the 2nd binding does NOT exercise keyed), `stored`/`hybrid` detection, the `invariants` block (test during living-docs — maybe-in), hook failure-semantics, breadth/cascade. Reuse pm's `validation-severity` tokens via reference (COR-019), don't grow a new taxonomy. Living-docs genuinely disagrees with pm on ≥1 axis (singleton vs keyed) → grounded extraction.

**Artifact tier.** **One COR** (foundational: backbone owns the process shape + engine; capabilities bind instances; vocabulary lock; name-broad/ship-narrow with the deferred features as named hypotheses) — **must be `accepted` before pm rebind or living-docs build** (acceptance gate; the sequencing blocker). **No ADR** (the substrate propagates to adopters → methodology surface → COR territory, not project-internal). **Two capability DECs** (pm rebind; living-docs binding). G-5 definition-versioning stays a named hypothesis.

## General substrate shape (draft, 2026-06-21)

Designed against all four instances + adopter apps. Every slot named (general); ★ = behavior ships now, ◇ = slot designed, behavior accretes on demand (COR-016 name-broad/ship-narrow).

```yaml
# ─── A PROCESS DEFINITION (a discipline authors this; conforms to the backbone shape) ───
process:
  id:        <slug>                 # ★ the process name (living-docs-adoption, issue-lifecycle, design-maturity, trip-planning)
  version:   <int>                  # ★ definition version — handles "definition changed under live subjects" (G-5)

  subject:                          # what carries position
    cardinality: singleton | keyed  # ★ singleton (living-docs) | ◇ keyed (issues/screens/POIs)
    key:         <field>            # ◇ (keyed only) what identifies each unit
    domain_ref:  <pointer>          # ★ where the subject's *domain* data lives — kept DISTINCT from position (D1 refinement)

  states:
    - id:      <slug>               # ★
      meaning: <prose>              # ★ D-obs, mandatory (but see prose-rot note below)
      detection:                    # how the engine resolves "is the subject in this state?"
        mode:      inferred | stored | hybrid   # ★ inferred | ◇ stored | ◇ hybrid
        predicate: <ref>            # ★ (inferred) a checkable predicate over reality / domain_ref
      entry:    <guard?>            # ★ start state? guarded — MULTIPLE entries allowed (living-docs brownfield vs greenfield)
      terminal: <bool>             # ★ end state? (living-docs "keeping-current")

  transitions:
    - from: <state> | "*"          # ★ "*" + back-edges + self-loops all expressible (deepen loops, pm self-loops)
      to:   <state>                # ★
      trigger:       <command>     # ★ the named action that drives it
      authorisation: user | agent-autonomous | script   # ★ D3 — *who* may move
      gate:                        # ★ D3 — *what* must hold; MUST be checkable
        kind: deterministic | authorisation-artifact
        predicate: <ref>           # ★ (deterministic) the engine runs it
        artifact:                  # ◇ (authorisation-artifact) the engine confirms it exists
          produced_by: <authority> # ◇ G-2 cross-authority — MUST differ from the gated actor (merge button, reviewer, CI, human)
          check:       <ref>
      severity:       <ref>        # ★ reuse pm's validation-severity tokens via COR-019 (no new taxonomy)
      why:            <prose>      # ★ D-obs
      condition_hint: <prose>      # ★ D-obs — explicitly SUBORDINATE to the live precheck (G-3)
      hint:           <command>    # ★ D-obs — what to run next
      hooks:                       # ◇ slot named; ship when a binding declares its first hook
        - action: <ref>
          kind:   integral | reactive   # ◇ integral=move rolls back on failure; reactive=logged warning
      breadth:        <ref>        # ◇ this move affects RELATED subjects (pm cascade / ux-ui journey-spawn) — altitude-2

  invariants:                      # ◇ slot named; ship if living-docs' "every doc registered with intent" can't be a gate (D4)
    - id:        <slug>
      condition: <ref>             # position-independent predicate
      scope:     always | [states]
      severity:  <ref>
      why:       <prose>

  orchestration:                   # ◇ altitude-2, entirely named-deferred (the "workflow"/"orchestration" layer)
    overflow:    []                # ◇ a terminal state hands a unit to ANOTHER process (design → implementation)
    cross_gates: []                # ◇ a move here needs ANOTHER process's state/approval

# ─── PER-SUBJECT RUNTIME (the "memory") ───
position: <state-id>               # ★ resolved per subject (stored, or derived for inferred)
journal:                           # ★ D-obs append-only: {ts, subject, from→to, trigger, actor, gate-result, severity, bypass+reason, hook-results}
blocked:                           # D6 STILL OPEN — derived "no legal move" vs first-class flag {blocked_on, resume_when} (CA-1)

# ─── ENGINE CONTRACT (backbone-owned, the real "process machine", central in BOTH A and B) ───
#   status        ★  → position + why + journal-tail + legal moves + LIVE prechecks + hints   (D-obs, narrative | --json)
#   can-i-move T  ★  → validate the move (gate precheck + authorisation); refuse with reason   (D3)
#   move T        ★  → execute: run integral hooks → on success journal → run reactive hooks    (D3/D5)
#   validate      ◇  → run in-scope invariants continuously                                     (D4)
```

### Coverage — the shape against every instance (proves it's not one-case-fit)

| Instance | subject | detection | notable transitions/gates | breadth / orchestration | invariants |
|---|---|---|---|---|---|
| **pm** | keyed (issues, tree) | inferred (branch/PR) | merge = authorisation-artifact (merge button = cross-authority) | cascade (breadth); pm-as-tracker (orchestration) | — |
| **ux-ui-design** | keyed (screens) | inferred+stored | reviewer = authorisation-artifact; strict-order/lenient-complete | journey-spawn (breadth); design→impl (overflow) | — |
| **trip-planning** | keyed (POIs/areas) | inferred (draft→verified ≠ position) | verify gate, saturation = deterministic; human pauses | per-area fan-out (breadth) | evidence-backed, scope-envelope (continuous) |
| **living-docs** | **singleton** | inferred (registry state) | brownfield/greenfield = multiple guarded entries; consolidate→transform→keep-current | — | every doc registered with intent |
| **adopter app** | either | either | its own staged gates | its own | its own |

living-docs (singleton) and pm (keyed) **disagree on cardinality** → the first two bindings genuinely exercise the seam, not a pm-shaped mould.

### What ships first (the narrow behavior, general design intact)

★ only: `singleton` + `inferred` + guarded transitions (forks/loops) + position + journal + `status`/`can-i-move`/`move`. Everything ◇ is *designed into the shape now* but implemented when a real binding reaches for it. pm rebinds onto ★ (its cascade stays pm-local in a ◇ slot until altitude-2); living-docs is built entirely on ★.

### Structural-determinism spectrum (proposed refinement, 2026-06-21)

Answers "what if the next steps/gates are resolved dynamically from data?" Four senses of "dynamic": (1) data-conditioned choice among known edges — already covered by guards; (2) data-parametrised instantiation (N units from data) — `keyed` + spawn; (3) **data-resolved selection over a *known* block vocabulary** (which blocks/order unknown until runtime); (4) genuinely open structure (novel steps from no known vocabulary).

Theory: nondeterminism adds no power to a finite machine (NFA≡DFA, subset construction), and a static graph + data-guards expresses any data-driven branching — so **senses 1–3 reduce to a deterministic *graph* (a run = a data-chosen path), provided the block alphabet is finite + known.** Caveat: static enumeration can blow up → a runtime *resolver* is often the better representation at equal power. Sense 4 (unknown alphabet) is genuinely irreducible (finite-state vs open/generative boundary) → needs an escape hatch, not a fuller enumeration.

Design — one shape, three modes; **the engine stays a deterministic validator across all of them**:
- **static** ★ — `to`/`gate` enumerated in the definition.
- **resolved** ◇ — `to`/`gate` is a named `resolver(data)` returning *which known blocks apply now*; deterministic-given-data (definite output → honest `status`/`can-i-move`).
- **open region** ◇ — a state kind marked *unstructured*: no internal edges, governed only by `invariants` + an explicit exit gate; the engine drops to a deterministic boundary check.

Net: a dynamic process never costs deterministic memory/validation. Adds two ◇ slots — a transition **resolver**, and an **open-region** state kind. Lets ux-ui-design be modelled as a graph with resolved edges + optional open region rather than a rigid pipeline (discovered by building, not imagined up front).

### Process composition — orchestration model (proposed refinement, 2026-06-21)

How a process embeds another process as a reusable, **parent-agnostic** block (build complex structures). Black-box composition (statecharts / BPMN call-activity / function composition):

- A process declares a **public interface**: `inputs` (what it needs to start) + `outcomes` (its named **terminal states** a caller can branch on).
- A parent embeds it via a `kind: subprocess` state: `runs: <capability>:<process-id>`, supplies `inputs` on entry, and wires the child's `outcomes` → the parent's own transitions (`gate: {outcome: …}`).
- **All coupling lives in the parent.** The child references nothing upward → reusable across parents, ignorant of all of them (dependency inversion, like a function signature).

Two flavors, same interface: **nest/call** (parent *waits* for an outcome — hierarchical, arbitrary depth) vs **overflow/hand-off** (terminal *spawns/unblocks* another process, concurrent — the earlier `overflow`). Distinct from pm's containment tree (same process, nested subjects).

Guarantees preserved: engine stays deterministic (subprocess exit = child reaching a *declared outcome*, definite; each level independently validatable); observability nests (`status` drills down; **journals link across levels** — composition is linked journals, answering "per-subject journal can't represent multi-level events"). Guard: definition-time check against recursive embedding cycles.

**Reinforces placement B:** embedding requires addressing a process by `<capability>:<process-id>` — exactly the existing reference scheme. Under B each process is self-contained *and* addressable = literally a composable block, no grammar change. Composability is a vote for B.

Scope: altitude-2 / ◇ (named now, behavior ships when a binding first nests). Adds slots: process `interface` (inputs + outcomes) and `kind: subprocess` (+ outcome-wiring), alongside `overflow`/`cross_gates`.

## Process discipline for this work

- Decisions locked here one at a time, with the user.
- Before any schema is authored: `critic` then `architect` (new shared primitive, cross-capability).
- Then `schema` skill to author; pm/ux-ui-design bind; migration if pm's shape moves (COR-010).

## Lifecycle

Retire to `done/` when the primitive crystallises (cite the resulting record(s) + schema + the first binding). Drop if it proves overfit with no general extraction.
