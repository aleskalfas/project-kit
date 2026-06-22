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
    blocked:                        # core (optional, COR-034)  a first-class WAIT — orthogonal, NOT a state
      blocked_on: awaiting-human | awaiting-condition | awaiting-subprocess-outcome   # core   WHY it waits (awaiting-subprocess-outcome is COR-036, single-inner; open to additive widening — deadlock deferred)
      resume_when: <predicate>      # core      REQUIRED for awaiting-condition, FORBIDDEN for awaiting-human; re-evaluated LIVE, auto-clears the flag when it holds
      assignee:    <owner?>         # core      optional: who owns the wait (audit colour)

  states:
    - id:      <slug>               # core
      meaning: <prose>              # core      load-bearing: the status view renders from it
      detection:
        mode:      inferred         # core: inferred (predicate over reality)  |  deferred: stored | hybrid
        predicate: <ref>            # core      a checkable predicate
      subprocess:                   # core (optional, COR-036)  this state EMBEDS an inner process
        runs:    <capability>:<id>  # core      the inner process address
        subject: <inner-id?>        # core      determinate inner subject id (REQUIRED for a keyed inner; omitted for singleton)
        inputs:  { ... }            # core      static input values supplied to the inner on entry
      entry:    <guard?>            # core      start state? guarded; MULTIPLE entries allowed
      terminal: <bool>             # core      end state? (also a process OUTCOME for composition — COR-036)

  transitions:
    - from: <state> | "*"          # core      back-edges + self-loops expressible
      to:   <state>                # core: static target  |  deferred: a resolver(data) over a known block set
      trigger:       <command>     # core      the named action
      authorisation: user | agent-autonomous | script   # core   WHO may move
      gate:                        # core      WHAT must hold — must be checkable (see below)
        kind: deterministic | authorisation-artifact | subprocess-outcome   # core: subprocess-outcome (COR-036) — engine-computed from an embedded inner outcome
        outcome: <inner-state>     # core (subprocess-outcome)  the inner OUTCOME this move leaves the subprocess state on
      severity:      <ref>         # core      a validation-severity token (reused, not re-invented)
      why:           <prose>       # core      status view
      hint:          <command>     # core      what to run next
      prompt:        <question>    # core (optional, COR-034)  the QUESTION posed on an awaiting-human move (user-auth only)
      hooks: [...]                 # deferred  on-move actions (integral | reactive)
      breadth: <ref>               # deferred  this move affects RELATED subjects (cascade / journey-spawn)

  invariants:                      # core (optional, COR-035)  position-independent always-checks, run by `validate` + surfaced on status
    - id:    <slug>                # core      stable identifier
      check: <predicate>           # core      the predicate (same shape as detection/gates); True = holds; indeterminate is fail-closed
      why:   <prose>               # core      explanatory prose surfaced on a violation
  interface:                       # core (optional, COR-036)  composition: { inputs, outcomes } — the public embedding contract
    inputs:   [{ name, meaning?, required? }]   # core      what the inner needs to start
    outcomes: [{ name, meaning? }]              # core      named terminal states a parent may wire
  orchestration: { overflow, cross_gates }   # deferred  altitude-2 (overflow / hand-off — concurrent spawn)
```

### Subject cardinality (core)

A process declares `subject.cardinality`:

- **`singleton`** — one journey per process. No subject identifier; the engine tracks the single journey under a fixed internal key.
- **`keyed`** (COR-032) — many units under one definition, each at its own position (e.g. one per issue). The engine operates **per a supplied subject identifier**: it resolves *that* subject's position, validates and executes *its* moves, and writes *its* journal, threading the identifier through every predicate it runs (as the predicate's first argv). The identifier is **required** for a keyed process — there is no singleton default; `pkit process … --subject <id>` must be given, and the engine errors clearly if it is missing. A keyed subject may declare a descriptive `key` naming what identifies a unit (e.g. `issue-number`); the engine does not interpret it, but subject identifiers must be safe to use in the per-subject journal path.

The engine **never enumerates** a keyed process's subjects — it only ever acts on the one it is given. Cross-subject enumeration and cascade across a containment tree are *breadth* (altitude-2) and remain deferred; a binding that needs them carries them capability-local (e.g. pm's parent/child cascade lives in its wrappers, not the engine).

Per-subject **runtime**: a resolved **position** (core), an append-only **journal** (core) — `{ts, subject, from→to, trigger, actor, gate-result, severity, bypass+reason}`, the memory, the how-we-got-here, and the audit trail in one — and a derived **blocked** detection (core, "no legal move") with an optional first-class `blocked{blocked_on, resume_when, assignee?}` wait (core — see below).

### Blocked — a first-class wait (core)

[COR-034](../decisions/core/COR-034-human-pause-gate.md) un-defers the human-pause / blocked slot. A subject may carry a `blocked` declaration on its `subject` block; the engine derives whether the subject is *currently* blocked **live** and clears it per its reason — by the person taking the pending move (`awaiting-human`) or by a `resume_when` predicate turning true (`awaiting-condition`).

**Authored** (in the definition, additive — absent on every existing process, which validate byte-unchanged):

```
subject:
  blocked:
    blocked_on: awaiting-human | awaiting-condition   # WHY it waits (open to additive widening)
    resume_when: <predicate>                          # awaiting-condition ONLY (required); forbidden for awaiting-human; re-evaluated LIVE, auto-clears
    assignee:    <owner?>                              # optional: who owns the wait (audit colour)

transitions:
  - from: ...
    authorisation: user
    prompt: <question>                                # optional: the QUESTION posed to the person (awaiting-human)
```

- **`blocked_on` ships three reasons**, each establishable from *one* subject's reality (COR-032): **`awaiting-human`** (a person must act), **`awaiting-condition`** (an external fact must become true), and **`awaiting-subprocess-outcome`** (COR-036, single-inner: the subject is parked in a `subprocess` state whose embedded inner has not yet reached a wired terminal outcome — see Composition below). The enum stays open to additive widening — the remaining cross-subject reason `deadlock` (a peer-subject cycle) joins it where the engine first reads across a *crowd* of subjects (deferred).
- **The blocked flag is a DERIVED overlay, recomputed live — never stored truth. Resume differs by reason** (COR-034):
  - **`awaiting-human`** carries **no `resume_when`** (the schema forbids one). It is *currently* blocked while the subject sits at a non-terminal position with an outgoing, **not-yet-taken** `user` move — whether that move's gate is open (ready to take) or closed (the human must intervene in reality first). The **resume is the person taking the move** — the position advancing off the parked state, which removes the pending move. The engine consults **no side-predicate**: a side-fact existing (e.g. a review file) must **not** clear an "approve?" block — only taking the move does. (Tying the resume to a side-predicate is forbidden precisely because the two can disagree: a satisfied side-fact while the move is still gate-closed would falsely report "not waiting" on a subject that is genuinely stuck.)
  - **`awaiting-condition`** carries a **required `resume_when`** predicate. It is *currently* blocked when (a) it has **no legal move** (the shipped "no legal move" detection — a non-terminal, determinate position out of which no transition is allowed), and (b) its `resume_when` predicate does **not** yet hold. When `resume_when` holds, the engine **auto-clears** the flag — the external fact turning true with no human in the loop. An indeterminate `resume_when` is fail-closed (the subject stays blocked rather than silently resuming).
  - **`awaiting-subprocess-outcome`** (COR-036, single-inner) carries **no `resume_when`** (the schema forbids one, like `awaiting-human`). It is *currently* blocked while the subject sits in a `subprocess` state with **no legal move** — i.e. no `subprocess-outcome` gate currently passes, because the embedded inner process has not reached a *wired* terminal outcome. It is **auto-clearing** like `awaiting-condition`, but the "condition" *is* the recursive resolution carried by the `subprocess-outcome` gates (re-evaluated live in the "no legal move" check) — when a wired inner outcome resolves, a gate opens, a legal move exists, and the wait clears with no human in the loop. A parent parked on an **unwired** inner outcome stays correctly blocked (the author owns outcome→transition wiring, not the engine).
- **The wait is journaled on enter and on resume.** Entering a blocked position appends a `blocked-enter` event; clearing it appends a `blocked-resume` event (each a journal entry — there is *no* separate emission/dispatch channel; the deferred **hooks** slot will react to these journaled transitions when it ships). `since` (the wait's age) is read from the open `blocked-enter` entry; `assignee` is carried from the declaration. **The journal is the audit trail; the CURRENT blocked-ness is always the live evaluation** (for `awaiting-human`, whether the pending move has been taken; for `awaiting-condition`, the `resume_when` predicate), **authoritative over any journal entry** (inheriting the journal-is-intent-log / live-detection-authoritative contract below).
- **Where the journaling happens.** `status` and `evaluate_blocked` are **read-only** (status runs predicates live and must not write). The journaling of enter/resume rides the writing paths only: `move` reconciles the wait against the **target state it just declared**, so a move that parks the subject journals the `blocked-enter` **at park time** — making `since` meaningful immediately, rather than lazily only once the human finally acts — and a move that clears the wait journals the `blocked-resume`. `reconcile_blocked` is also exposed (with no target override) so a binding can journal a self-clearing `awaiting-condition` resume — which needs no human move — on demand against live reality. Because live detection is authoritative, a not-yet-journaled resume never lies about current state.
- **An `awaiting-human` block carries a `prompt`** — the question — authored on the `user` move and surfaced on that move's per-move emission (and lifted onto the blocked overlay for the human-pause view). The park stops being a silent "your move" and becomes "your move: here's the question." Content-free: the engine carries/surfaces `prompt` and `blocked_on` but never interprets them.
- **It is orthogonal, not a state.** It annotates the subject at its current position; it adds no state to the process and cannot explode the state space. Position stays inferred; the validator stays deterministic (`resume_when` is a predicate over reality, exactly like detection).

**Deferred** (each its own future decision when a binding needs it, per COR-034): the remaining cross-subject `blocked_on` reason `deadlock` (a peer-subject cycle — distinct from COR-036's acyclicity guard), the **hooks** firing mechanism (notify-on-enter / act-on-resume), and a structured **`selection`** option-set (render options in the prompt text until it ships). (`awaiting-subprocess-outcome` shipped with composition — COR-036.)

### Invariants — position-independent always-checks (core)

[COR-035](../decisions/core/COR-035-process-invariants.md) un-defers the invariants slot. Where detection answers "where is this subject?" and a gate answers "may it move from here to there?", an **invariant** answers a third, position-independent question: "is something that must *always* be true, true?". A process may declare a list of them on the `process` block; each holds **process-wide** (across every state).

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
process:
  invariants:
    - id:    <slug>          # stable identifier (reported by validate + on status)
      check: <predicate>     # the predicate — SAME shape detection/gates use; True = holds
      why:   <prose>         # explanatory prose surfaced when the check fails
```

- **Position-independent.** An invariant is checked irrespective of where the subject is — a property of *being* anywhere in the process, not of *moving*. The engine evaluates it against current reality regardless of the resolved position (an indeterminate or absent position does not stop it being checked).
- **Read-only, content-free, single-subject.** The engine *runs* each `check` through the **same predicate runner that backs detection and gates** (single-subject, threaded with the subject id) and *reports* the result with the `why` on failure; it never interprets what the invariant means and never reads across subjects (COR-032). An indeterminate `check` (error / timeout / unparseable / unresolved) is **fail-closed** — reported as NOT holding (a check that cannot be confirmed is treated as a violation, mirroring `resume_when`).
- **Report-only enforcement, surfaced on every status read.** A violation is **surfaced on the status view** (the load-bearing half — an agent reading status sees it every read, and a binding's wrapper declines downstream) and reported by the dedicated **`validate`** operation (`pkit process validate <address>` — narrative or `--json`, exits non-zero on any violation). It does **not** block moves, fail transitions, or remediate; a binding that wants a hard always-gate expresses it as a gate predicate. The status narrative shows only *violations* (to stay terse); `status --json` and `validate` carry the full set.
- **Determinism preserved.** An invariant is a predicate over reality, exactly like a detection predicate — position stays inferred and the engine stays a deterministic validator.

**Deferred** (each its own future decision when a binding needs it, per COR-035): per-state (`applies-to`) **subset-scoping** and **boundary-enforcement** (move-blocking on violation) — both consumed by composition's **open region** (below) and landing *with* it; invariant **severity** / auto-remediation; and **cross-subject** always-checks (which require the breadth COR-032 holds back). This slot ships the *declaration* + report-only surface only.

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
- an **open region** (deferred) — a state with no internal edges, bounded only by `invariants` + an explicit exit gate (the engine drops to a deterministic boundary check). The `invariants` *declaration* now ships (COR-035), but the open region needs more than that: it needs those invariants in a **boundary-enforcing** posture (constraining legal movement, not report-only) **plus** per-state (`applies-to`) scoping — both still deferred, landing together when the open region ships. So "invariants is a prerequisite for the open region" is true of the declaration only.

In every mode the engine remains a deterministic validator. (Theory: for a finite, known block alphabet this is equivalent to a static graph; the open region is the escape hatch for genuinely open-ended work.)

## Composition — cross-process outcome resolution (core)

[COR-036](../decisions/core/COR-036-process-composition.md) un-defers the composition slot and gives the engine its one genuinely-new capability: **resolve another process's terminal outcome** and read it as an input to a parent's gate. A process exposes a public **interface** = `inputs` (what it needs to start) + `outcomes` (its named terminal states — a `terminal: true` state *is* an outcome). A parent embeds *one* inner process via a **`subprocess` state** that `runs: <capability>:<process-id>`, supplies the inner's inputs on entry, and wires the inner's outcomes to its own outgoing transitions. **All coupling lives in the parent**; the child references nothing upward, so it is reusable and parent-agnostic.

This ships the **nest/call** timing (a parent waits for an inner outcome). The **overflow/hand-off** timing (a terminal state spawning or unblocking a *concurrent* sibling process — altitude-2 orchestration) and the **enumerate-and-fold aggregate** across many inner subjects (cascade) remain deferred.

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
process:
  interface:                       # the public embedding contract
    inputs:   [{ name, meaning?, required? }]
    outcomes: [{ name, meaning? }]   # each names a terminal state id
  states:
    - id: <subprocess-state>
      meaning: <prose>
      detection: { mode: inferred, predicate: <ref> }   # "is the subject parked in this stage?" — the parent's own reality
      subprocess:
        runs:    <capability>:<process-id>   # the inner process address
        subject: <inner-id?>                 # REQUIRED for a keyed inner (COR-032); omitted for a singleton inner
        inputs:  { <name>: <value> }         # static input values supplied to the inner on entry
  transitions:
    - from: <subprocess-state>
      to:   <next>
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome             # the ENGINE computes this — no capability predicate
        outcome: <inner-terminal-state>      # the move opens iff the inner reached exactly this outcome
```

- **One *determinate* inner — the engine never enumerates.** The engine resolves the outcome of **one** inner process whose subject is determinate: either the inner is `singleton` (no id), or the `subprocess.subject` supplies the one keyed inner id. A keyed inner with no supplied subject is **fail-closed** (COR-032's required-subject rule). It resolves *that one* and never enumerates a keyed inner's subjects — folding across many is the **cascade** consumer (deferred), which calls this resolution once per subject it enumerates.
- **The resolution is a recursive engine instantiation.** While the subject is parked in a `subprocess` state, the engine builds a *new* inner engine on the inner address + the determinate inner subject and reads the inner's terminal via the inner engine's own `resolve_position`. A `subprocess-outcome` gate on the parent is computed by the **engine** (not a capability predicate, like the `authorisation-artifact` kind): it passes iff the inner reached exactly the gate's named `outcome`. Resolution is **read-only** (running `status` resolves the inner but writes neither journal).
- **No cycles — the acyclicity guard.** A process may not embed itself, directly or transitively (A runs A; A runs B runs A). The engine tracks the active resolution stack (each engine's own address plus every inner above it) and refuses an address already on the stack, **failing closed** (surfaced, like an unrecognised gate kind) — a cyclic resolution never terminates, so it has no definite answer. This is distinct from COR-034's deferred `deadlock` (a peer-subject cycle, a different graph).
- **Waiting on the inner — `awaiting-subprocess-outcome`.** While the inner has not reached a *wired* terminal outcome, the parent has no satisfiable outgoing move and is parked as the `awaiting-subprocess-outcome` blocked reason (above) — an auto-clearing overlay whose "condition" is the live resolution. A parent parked on an **unwired** inner outcome is *correctly* still waiting (the author owns outcome→transition wiring), not a bug to special-case.
- **Determinism preserved (P3/P6).** A subprocess state's position *is* the inner's terminal outcome — itself inferred-from-reality by the inner's own deterministic detection. "Where is the subject?" reduces to "what outcome did the inner reach?", a composed definite answer; with cycles forbidden the composition terminates. Position stays inferred; the validator stays deterministic.

The `status` view surfaces the embedded inner and its live-resolved outcome (narrative: an `embeds <address>` / `inner outcome: <x>` line; `--json`: a `position.subprocess` object with `{runs, outcome, indeterminate, reason}`).

**Deferred** (each its own future decision when a binding needs it, per COR-036): the **enumerate-and-fold aggregate** + the **many-inner aggregate wait** across a keyed inner's subjects (cascade — it *consumes* this single-inner resolution as its per-subject step); the **overflow / hand-off** (concurrent spawn) timing and the broader **orchestration** altitude.

## The engine

The backbone exposes the engine as a `pkit process …` surface. The core operations:

| Operation | Answers / does |
|---|---|
| `status` | where the subject is · why · how it got here (journal) · legal moves with live prechecks · next hint — narrative or `--json` |
| `can-move <to>` | validate a candidate move (gate precheck + authorisation); refuse with a self-explaining reason |
| `move <to>` | execute a legal move; record the journal entry (and run hooks, deferred) |
| `validate` | run the subject's invariants (COR-035) and report which hold / are violated — narrative or `--json`; exits non-zero on any violation |

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
3. The process is addressable elsewhere as `<capability>:<process-id>` — a parent embeds it by that address through a `subprocess` state (composition, COR-036). Orchestration (concurrent hand-off) remains deferred.

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
