---
variant: specialized
---

# Process

The shared **process substrate** — a content-free state machine that any discipline binds its own staged, gated process to. Decided in [COR-033](../decisions/core/COR-033-process-substrate.md): the backbone owns the *shape contract* and the *engine*; each capability ships its own *process definition* as an instance that conforms to the shape. The substrate gives every process two guarantees for free — a deterministic **validator** of each move, and a self-explaining **memory** of where each subject stands — so an automated agent can rely on it for "where am I / may I move / am I valid", and a human with no manual can read the same answers.

This README is the authoritative spec; the full design rationale (incl. the `critic` and `architect` reviews) lives in `.pkit/scratchpad/active/2026-06-21-process-primitive.md`.

Two markers appear below: **core** — ships in the minimal first cut; **deferred** — a named extension point designed into the shape now, but built only when a real binding needs it (name-broad / ship-narrow, per COR-016).

## Vocabulary — one substrate, two altitudes

- **State machine** — the content-free substrate: states, guarded transitions, a position, a journal. Knows nothing about issues, screens, docs, or trips.
- **Process** (depth) — one discipline's substrate-bound journey over its own subjects. The thing a capability authors.
- **Orchestration** (breadth, deferred) — a system of interacting processes (one process embeds or hands off to another). The same substrate one altitude up.

A discipline's existing lifecycle artifact (e.g. an issue-lifecycle `workflow.yaml`) is, under this vocabulary, a *process definition* and keeps its own name.

## The shape

A **process definition** (a capability authors one) declares the following. Each line notes whether it is *core* or *deferred*:

```
process:
  id:        <slug>                 # core      addressable as <capability>:<id>
  version:   <int>                  # core      definition version (handles definition changes under live subjects)
  subject:
    cardinality: singleton          # core: singleton (one journey)  |  core: keyed (many units, e.g. per issue/screen — COR-032)
    key:         <slug>             # core (keyed)  descriptive name of what identifies a unit (e.g. issue-number); engine does not interpret it
    domain_ref:  <pointer>          # core      where the subject's DOMAIN data lives — distinct from its process position

  states:
    - id:      <slug>               # core
      meaning: <prose>              # core      load-bearing: the status view renders from it
      detection:
        mode:      inferred         # core: inferred (predicate over reality)  |  deferred: stored | hybrid
        predicate: <ref>            # core      a checkable predicate
      entry:    <guard?>            # core      start state? guarded; MULTIPLE entries allowed
      terminal: <bool>             # core      end state? (also a process OUTCOME for composition)

  transitions:
    - from: <state> | "*"          # core      back-edges + self-loops expressible
      to:   <state>                # core: static target  |  deferred: a resolver(data) over a known block set
      trigger:       <command>     # core      the named action
      authorisation: user | agent-autonomous | script   # core   WHO may move
      gate:                        # core      WHAT must hold — must be checkable (see below)
        kind: deterministic | authorisation-artifact
      severity:      <ref>         # core      a validation-severity token (reused, not re-invented)
      why:           <prose>       # core      status view
      hint:          <command>     # core      what to run next
      hooks: [...]                 # deferred  on-move actions (integral | reactive)
      breadth: <ref>               # deferred  this move affects RELATED subjects (cascade / journey-spawn)

  invariants: [...]                # deferred  position-independent always-checks, run by `validate`
  interface:                       # deferred  composition: { inputs, outcomes } — the public contract
  orchestration: { overflow, cross_gates }   # deferred  altitude-2
```

### Subject cardinality (core)

A process declares `subject.cardinality`:

- **`singleton`** — one journey per process. No subject identifier; the engine tracks the single journey under a fixed internal key.
- **`keyed`** (COR-032) — many units under one definition, each at its own position (e.g. one per issue). The engine operates **per a supplied subject identifier**: it resolves *that* subject's position, validates and executes *its* moves, and writes *its* journal, threading the identifier through every predicate it runs (as the predicate's first argv). The identifier is **required** for a keyed process — there is no singleton default; `pkit process … --subject <id>` must be given, and the engine errors clearly if it is missing. A keyed subject may declare a descriptive `key` naming what identifies a unit (e.g. `issue-number`); the engine does not interpret it, but subject identifiers must be safe to use in the per-subject journal path.

The engine **never enumerates** a keyed process's subjects — it only ever acts on the one it is given. Cross-subject enumeration and cascade across a containment tree are *breadth* (altitude-2) and remain deferred; a binding that needs them carries them capability-local (e.g. pm's parent/child cascade lives in its wrappers, not the engine).

Per-subject **runtime**: a resolved **position** (core), an append-only **journal** (core) — `{ts, subject, from→to, trigger, actor, gate-result, severity, bypass+reason}`, the memory, the how-we-got-here, and the audit trail in one — and a derived **blocked** detection (core, "no legal move") with an optional first-class `blocked{blocked_on, resume_when}` flag (deferred).

## The two guarantees

- **Deterministic validator.** Given a definition and observable reality, "where is this subject", "may it move here→there", and "is it valid" are *definite* answers. This holds even for dynamic structure (below).
- **Self-explaining memory.** The status view renders where the subject is, why, how it got there, what it may do next — each with a **live precheck**, and the live precheck is authoritative over any prose label. Two renderings: narrative (human) and structured (agent/machine).

## Gate-checkability (the load-bearing rule)

Every transition gate reduces to one of:

- a **deterministic predicate** the engine evaluates over the subject's artifact / domain state, or
- a **recorded authorisation artifact** the engine confirms exists **and that was produced by a different authority than the actor being gated** (cross-authority — e.g. a human merge, a reviewer verdict, a CI check).

An actor's own assertion that a gate passed is **never** sufficient — a judgment gate must leave a cross-authority, checkable trace, or validation is theatre.

## Determinism across dynamic structure (deferred)

A process need not be a rigid pipeline. A transition target/gate may be:

- **static** (core) — enumerated in the definition;
- **resolved** (deferred) — a `resolver(data)` returning which of a *known* set of blocks apply now (deterministic given the data → the engine stays an honest validator);
- an **open region** (deferred) — a state with no internal edges, bounded only by `invariants` + an explicit exit gate (the engine drops to a deterministic boundary check).

In every mode the engine remains a deterministic validator. (Theory: for a finite, known block alphabet this is equivalent to a static graph; the open region is the escape hatch for genuinely open-ended work.)

## Composition (deferred)

A process exposes a public **interface** = `inputs` (what it needs to start) + `outcomes` (its named terminal states). A parent embeds it via a `subprocess` state that `runs: <capability>:<process-id>`, supplies inputs on entry, and wires the child's outcomes to its own transitions. **All coupling lives in the parent**; the child references nothing upward, so it is reusable and parent-agnostic. Two timings: *nest/call* (parent waits for an outcome) and *overflow/hand-off* (terminal spawns/unblocks another process, concurrent).

## The engine

The backbone exposes the engine as a `pkit process …` surface. The core operations:

| Operation | Answers / does |
|---|---|
| `status` | where the subject is · why · how it got here (journal) · legal moves with live prechecks · next hint — narrative or `--json` |
| `can-move <to>` | validate a candidate move (gate precheck + authorisation); refuse with a self-explaining reason |
| `move <to>` | execute a legal move; record the journal entry (and run hooks, deferred) |
| `validate` | run in-scope invariants (deferred) |

The engine is **content-free**: it reads any capability's process definition + that subject's reality and resolves/validates against it. Capability commands (the discipline's verb-subject wrappers) supply the definition + subject + any domain side-effects and delegate the state-machine mechanics to the engine.

**Code home (ADR-020).** The engine ships in the `pkit` binary (`src/project_kit/process.py`), invoked only as `pkit process …`; the engine *code* is not propagated to adopters (only this spec, the shape contract, and the journal home are). Capability wrappers call the engine by **subprocess**, never by import.

### The predicate runner (engine contract)

A predicate's `run:` resolves to a command the owning capability **registers** in its `package.yaml` — not a raw path or shell string; the engine rejects an unregistered name with a self-explaining error. The engine invokes the resolved script as a plain subprocess (explicit argv — the subject + `--json`), with the working directory at the repo root, reads structured JSON, and:

- **deterministic gate / detection** → uses the predicate's `result`;
- **authorisation-artifact gate** → reads `{ exists, produced_by }` and computes `result = exists && produced_by != actor` *itself* — the engine enforces cross-authority and **ignores any `result` the predicate supplies** (non-overridable).

Predicates **must be read-only** — `status` runs them live, so a mutating predicate would be a side-effect bug.

**Failure is fail-closed.** A predicate that errors, times out, returns unparseable JSON, or doesn't resolve is **indeterminate**: `status` shows it distinctly ("couldn't evaluate: …") and `move` refuses. An unrecognised or schema-future gate (engine/definition version skew) likewise fails closed — never a silent pass. Gates are correctness boundaries (unlike the permission hook's fail-open *availability* posture).

**Performance.** Resolve position first (run detection predicates), then precheck only the transitions *out of* the current state; evaluate each predicate at most once per `(command, args)` per invocation. No cross-invocation position caching — that is the deferred `stored` detection mode.

### Seam-ordering contract (journal-as-intent-log)

This is canonical guidance for **all** bindings — how a capability wrapper sequences its own domain side-effect against the engine's journal write.

The journal is an **intent log, not the source of truth**. Live detection is authoritative (COR-033 P3): a subject's position is always re-derived by running the detection predicates against current reality, never read back from the journal. So the journal entry the engine appends on a legal `move` records *that a move was taken*, but the next `status` reports the *real* inferred position regardless of what the journal says.

The ordering a wrapper follows:

1. The wrapper validates and applies its **domain side-effect** (create the branch, open the PR, edit the label/board) — the change that will make live detection report the new state.
2. The wrapper calls `pkit process move` (by subprocess) to **journal** the move.

Because detection is authoritative, the seam is self-correcting in the failure case: if a wrapper's domain side-effect later fails (or partially fails) *after* a journal entry was written, the next `status` runs detection live and reflects the subject's **real** inferred position — the stale journal entry does not lie about where the subject is, it only records the attempt. A wrapper should still surface side-effect failures to its caller; the point is that a failed side-effect cannot corrupt the engine's notion of position. Wrappers must **read position from the engine** (`status --json`) rather than re-inferring it themselves, so there is one source of position truth.

## Binding a process (how a capability uses this)

1. Author a process definition as the capability's own instance schema at `.pkit/capabilities/<capability>/schemas/<process>.yaml`, declaring conformance to the shape contract (`../../../schemas/_defs/process.schema.json`).
2. Drive it through the capability's verb-subject commands, which call the engine.
3. The process is addressable elsewhere as `<capability>:<process-id>` (used by composition and orchestration, deferred).

The existing schema-binding grammar (COR-023) is unchanged; capabilities stay independent, self-describing peers.

## Layout

```
src/project_kit/process.py          # the engine (in the binary; ADR-020 — NOT propagated to adopters)
.pkit/process/
  README.md                         # this spec — the shape contract + engine contract (propagated)
.pkit/schemas/_defs/
  process.schema.json               # the shape contract as a JSON-Schema fragment (propagated;
                                    # capability instance schemas $ref it to inherit the shape)
.pkit/capabilities/<capability>/schemas/<process>.yaml
                                    # each capability's own conforming process definition (instance)
.pkit/capabilities/<capability>/project/process/<process-id>/<subject>.journal.jsonl
                                    # per-subject journal — append-only JSONL, COMMITTED (it is the
                                    # audit trail), in the capability's adopter-owned project/ subtree
                                    # (sync-safe; the engine owns the path, capabilities don't declare it)
```

The engine ships as a backbone CLI surface (`pkit process …`) homed in the binary per ADR-020 — capabilities never re-implement the state machine, they bind to it. The journal is project-owned, committed data.

## Grounding & status

Per COR-033's acceptance-gate (COR-007 grounding), the substrate ships proven against two instances: the project-management process **rebound** onto it (its breadth / closure / PR-sub-lifecycle fields kept capability-local), and one new concrete binding as the grounded second instance. Each binding is its own capability decision (DEC); the pm rebind carries a COR-010 migration. The deferred extension points each become real — and gain their own decision — when a binding first needs one.
