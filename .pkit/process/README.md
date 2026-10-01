---
variant: specialized
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/process.py
        - src/project_kit/process_authoring.py
        - src/project_kit/process_dependencies.py
        - src/project_kit/process_graph.py
        - src/project_kit/process_health.py
        - src/project_kit/process_journal.py
        - .pkit/schemas/_defs/process.schema.json
      record: [COR-033, COR-034, COR-035, COR-036, COR-037, COR-038, COR-040, COR-042, COR-044, COR-053, ADR-020, ADR-036, ADR-048, ADR-051]
    revalidated:
      at: 2026-10-01T20:17:11Z
      outcome: unchanged
      unchanged-because: this change adds a view key to the health JSON payloads, makes a failed authoring stamp take back its writes, and rewords hand-off's refusal when one state holds two entries on an upstream; this page lists health as narrative or JSON without enumerating keys and states the stamps' contract (registered owning capability, fail-closed stubs, registration) without their failure handling, all of which still holds — the CLI reference carries the detail
---

# Process

The shared **process substrate** — a content-free state machine that any discipline binds its own staged, gated process to. Decided in [COR-033](../decisions/core/COR-033-process-substrate.md): the backbone owns the *shape contract* and the *engine*; each capability ships its own *process definition* as an instance that conforms to the shape. The substrate gives every process two guarantees for free — a deterministic **validator** of each move, and a self-explaining **memory** of where each subject stands — so an automated agent can rely on it for "where am I / may I move / am I valid", and a human with no manual can read the same answers.

This README is the authoritative spec; the full design rationale (incl. the `critic` and `architect` reviews) lives in `.pkit/scratchpad/done/2026-06-21-process-primitive.md`.

Two markers appear below: **core** — ships in the minimal first cut; **deferred** — a named extension point designed into the shape now, but built only when a real binding needs it (name-broad / ship-narrow, per COR-016).

## Vocabulary — one substrate, two altitudes

- **State machine** — the content-free substrate: states, guarded transitions, a position, and — where the project keeps one — a journal. Knows nothing about issues, screens, docs, or trips.
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
      blocked_on: awaiting-human | awaiting-condition | awaiting-subprocess-outcome | awaiting-cascade-outcome   # core   WHY it waits (awaiting-subprocess-outcome is COR-036, single-inner; awaiting-cascade-outcome is COR-037, the aggregate fold wait; open to additive widening — deadlock deferred)
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
      depends_on:                   # core (optional, COR-038)  INERT cross-process connection metadata — the engine and every gate NEVER read it
        - upstream: <capability>:<id> | <publisher>::<role>:<point>   # core   by implementation, or by role (COR-053) — the process a role's active provider offers
          relation: informational | gates-on-readiness | triggered-by | constrained-with   # core   CLOSED set (no composed-subprocess/aggregates — those are DERIVED)
          mode:     pull | push     # core      pull = read on the reader's turn  |  push = mediated OUTSIDE the engine (no eventing)
          why:      <prose>         # core      REQUIRED reason the render surfaces
          version:  <int>           # core (optional, COR-053)  the upstream INTERFACE version targeted — connects only at an equal one
          mandatory: { reason: <prose> }   # core (optional, COR-053)  the upstream must exist; read by the capability lifecycle only
      entry:    <guard?>            # core      start state? guarded; MULTIPLE entries allowed
      terminal: <bool>             # core      end state? (also a process OUTCOME for composition — COR-036)
      open_region: <bool>          # core (optional, COR-040)  free-order state: no internal edges, bounded by region-scoped invariants + one exit gate

  transitions:
    - from: <state> | "*"          # core      back-edges + self-loops expressible
      to:   <state>                # core: static target  |  deferred: a resolver(data) over a known block set
      trigger:       <command>     # core      the named action
      authorisation: user | agent-autonomous | script   # core   WHO may move
      gate:                        # core      WHAT must hold — must be checkable (see below)
        kind: deterministic | authorisation-artifact | subprocess-outcome | cascade-outcome   # core: subprocess-outcome (COR-036) — engine-computed from an embedded inner outcome; cascade-outcome (COR-037) — engine-computed from the process's `cascade` fold
        outcome: <inner-state>     # core (subprocess-outcome)  the inner OUTCOME this move leaves the subprocess state on
      severity:      <ref>         # core      a validation-severity token (reused, not re-invented)
      why:           <prose>       # core      status view
      hint:          <command>     # core      what to run next
      prompt:        <question>    # core (optional, COR-034)  the QUESTION posed on an awaiting-human move (user-auth only)
      hooks: [...]                 # deferred  on-move actions (integral | reactive)

  cascade:                         # core (optional, COR-037)  fold ONE child process's member outcomes into a gate
    runs:    <capability>:<id>     # core      the one named child process whose members are folded
    members:    <predicate>        # core      parent-scoped candidate-member SOURCE (returns { members: [...] }); the engine never enumerates the child's subjects
    membership: <predicate>        # core      per-subject "does THIS subject belong to this parent?" test (run one at a time)
    reducer:
      op:        all | count       # core      all = every member reached `outcome`  |  count = at least `threshold` did
      outcome:   <child-state>     # core      the child OUTCOME each member is folded against
      threshold: <int>             # core (count)  the saturation floor (forbidden for `all`)
  # the parent gate it feeds is a transition `gate: { kind: cascade-outcome }` (no predicate / outcome — the fold IS the check)

  invariants:                      # core (optional, COR-035)  position-independent always-checks, run by `validate` + surfaced on status
    - id:    <slug>                # core      stable identifier
      check: <predicate>           # core      the predicate (same shape as detection/gates); True = holds; indeterminate is fail-closed
      why:   <prose>               # core      explanatory prose surfaced on a violation
  interface:                       # core (optional, COR-036)  composition: { inputs, outcomes } — the public embedding contract
    version:  <int>                              # core (optional, COR-053)  the INTERFACE version — changes only when this contract breaks
    inputs:   [{ name, meaning?, required? }]   # core      what the inner needs to start
    outcomes: [{ name, meaning? }]              # core      named terminal states a parent may wire
  orchestration: { overflow, cross_gates }   # deferred  altitude-2 (overflow / hand-off — concurrent spawn)
```

### Subject cardinality (core)

A process declares `subject.cardinality`:

- **`singleton`** — one journey per process. No subject identifier; the engine tracks the single journey under a fixed internal key.
- **`keyed`** (COR-032) — many units under one definition, each at its own position (e.g. one per issue). The engine operates **per a supplied subject identifier**: it resolves *that* subject's position, validates and executes *its* moves, and writes *its* journal, threading the identifier through every predicate it runs (as the predicate's first argv). The identifier is **required** for a keyed process — there is no singleton default; `pkit process … --subject <id>` must be given, and the engine errors clearly if it is missing. A keyed subject may declare a descriptive `key` naming what identifies a unit (e.g. `issue-number`); the engine does not interpret it, but subject identifiers must be safe to use in the per-subject journal path.

The engine **never enumerates** a keyed process's subjects — it only ever acts on the one it is given. The **one** sanctioned, bounded exception is the **cascade fold** (COR-037, below): a parent reads across the members of *one declared child process* scoped to one parent subject, and only through a capability-supplied membership predicate run one subject at a time — never a containment tree the engine holds, never a general subject-listing API. Everywhere else the never-enumerate discipline is unchanged; pm's *forward* (position) cascade stays capability-local until a binding demands the shared form.

Per-subject **runtime**: a resolved **position** (core) and a derived **blocked** detection (core, "no legal move") with an optional first-class `blocked{blocked_on, resume_when, assignee?}` wait (core — see below). Beside them, **optional audit**: an append-only **journal** — `{ts, subject, from→to, trigger, actor, gate-result, severity, bypass+reason}`, the how-we-got-here — kept only where the project turns journal logging on (off by default; see "The journal" below). Nothing the engine decides reads it.

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

- **`blocked_on` ships four reasons.** Three are establishable from *one* subject's reality (COR-032): **`awaiting-human`** (a person must act), **`awaiting-condition`** (an external fact must become true), and **`awaiting-subprocess-outcome`** (COR-036, single-inner: the subject is parked in a `subprocess` state whose embedded inner has not yet reached a wired terminal outcome — see Composition below). The fourth, **`awaiting-cascade-outcome`** (COR-037), is the single sanctioned *cross-subject* fold wait: the subject is parked at a state whose outgoing `cascade-outcome` gate folds across one declared child process's members and has not yet resolved open (see Cascade below). The enum stays open to additive widening — the remaining cross-subject reason `deadlock` (a peer-subject cycle) joins it where the engine reads across a crowd of subjects in a *waiting* posture (deferred; the cascade fold is acyclic by construction — it waits only on members' already-resolved terminal outcomes).
- **The blocked flag is a DERIVED overlay, recomputed live — never stored truth. Resume differs by reason** (COR-034):
  - **`awaiting-human`** carries **no `resume_when`** (the schema forbids one). It is *currently* blocked while the subject sits at a non-terminal position with an outgoing, **not-yet-taken** `user` move — whether that move's gate is open (ready to take) or closed (the human must intervene in reality first). The **resume is the person taking the move** — the position advancing off the parked state, which removes the pending move. The engine consults **no side-predicate**: a side-fact existing (e.g. a review file) must **not** clear an "approve?" block — only taking the move does. (Tying the resume to a side-predicate is forbidden precisely because the two can disagree: a satisfied side-fact while the move is still gate-closed would falsely report "not waiting" on a subject that is genuinely stuck.)
  - **`awaiting-condition`** carries a **required `resume_when`** predicate. It is *currently* blocked when (a) it has **no legal move** (the shipped "no legal move" detection — a non-terminal, determinate position out of which no transition is allowed), and (b) its `resume_when` predicate does **not** yet hold. When `resume_when` holds, the engine **auto-clears** the flag — the external fact turning true with no human in the loop. An indeterminate `resume_when` is fail-closed (the subject stays blocked rather than silently resuming).
  - **`awaiting-subprocess-outcome`** (COR-036, single-inner) carries **no `resume_when`** (the schema forbids one, like `awaiting-human`). It is *currently* blocked while the subject sits in a `subprocess` state with **no legal move** — i.e. no `subprocess-outcome` gate currently passes, because the embedded inner process has not reached a *wired* terminal outcome. It is **auto-clearing** like `awaiting-condition`, but the "condition" *is* the recursive resolution carried by the `subprocess-outcome` gates (re-evaluated live in the "no legal move" check) — when a wired inner outcome resolves, a gate opens, a legal move exists, and the wait clears with no human in the loop. A parent parked on an **unwired** inner outcome stays correctly blocked (the author owns outcome→transition wiring, not the engine).
  - **`awaiting-cascade-outcome`** (COR-037, the aggregate fold wait) carries **no `resume_when`** (the schema forbids one, like `awaiting-subprocess-outcome`). It is *currently* blocked while the subject sits at a state whose outgoing `cascade-outcome` gate has **no legal move** — i.e. the fold over the declared child's members has not resolved open. It is **auto-clearing**, the "condition" being the live fold itself (re-evaluated live in the "no legal move" check) — when the fold resolves open (all members reached the outcome, or the threshold is met), the gate opens, a legal move exists, and the wait clears with no human in the loop. Fail-closed throughout: any unresolved member, and the empty member set, hold the fold shut (the parent stays correctly blocked).
- **The wait is journaled on enter and on resume — where the project keeps a journal.** With journal logging off the wait is exactly as live and as blocking, `reconcile_blocked` has nothing to record, and `since` is absent (see "The journal" below). With it on, entering a blocked position appends a `blocked-enter` event; clearing it appends a `blocked-resume` event (each a journal entry — there is *no* separate emission/dispatch channel; the deferred **hooks** slot will react to these journaled transitions when it ships). `since` (the wait's age) is read from the open `blocked-enter` entry; `assignee` is carried from the declaration. **The journal is the audit trail; the CURRENT blocked-ness is always the live evaluation** (for `awaiting-human`, whether the pending move has been taken; for `awaiting-condition`, the `resume_when` predicate), **authoritative over any journal entry** (inheriting the journal-is-intent-log / live-detection-authoritative contract below).
- **Where the journaling happens.** `status` and `evaluate_blocked` are **read-only** (status runs predicates live and must not write). The journaling of enter/resume rides the writing paths only: `move` reconciles the wait against the **target state it just declared**, so a move that parks the subject journals the `blocked-enter` **at park time** — making `since` meaningful immediately, rather than lazily only once the human finally acts — and a move that clears the wait journals the `blocked-resume`. `reconcile_blocked` is also exposed (with no target override) so a binding can journal a self-clearing `awaiting-condition` resume — which needs no human move — on demand against live reality. Because live detection is authoritative, a not-yet-journaled resume never lies about current state.
- **An `awaiting-human` block carries a `prompt`** — the question — authored on the `user` move and surfaced on that move's per-move emission (and lifted onto the blocked overlay for the human-pause view). The park stops being a silent "your move" and becomes "your move: here's the question." Content-free: the engine carries/surfaces `prompt` and `blocked_on` but never interprets them.
- **It is orthogonal, not a state.** It annotates the subject at its current position; it adds no state to the process and cannot explode the state space. Position stays inferred; the validator stays deterministic (`resume_when` is a predicate over reality, exactly like detection).

**Deferred** (each its own future decision when a binding needs it, per COR-034): the remaining cross-subject `blocked_on` reason `deadlock` (a peer-subject cycle — distinct from COR-036's acyclicity guard and from COR-037's acyclic-by-construction fold wait), the **hooks** firing mechanism (notify-on-enter / act-on-resume), and a structured **`selection`** option-set (render options in the prompt text until it ships). (`awaiting-subprocess-outcome` shipped with composition — COR-036; `awaiting-cascade-outcome` shipped with cascade — COR-037.)

### Invariants — position-independent always-checks (core)

[COR-035](../decisions/core/COR-035-process-invariants.md) un-defers the invariants slot. Where detection answers "where is this subject?" and a gate answers "may it move from here to there?", an **invariant** answers a third, position-independent question: "is something that must *always* be true, true?". A process may declare a list of them on the `process` block; each holds **process-wide** (across every state).

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
process:
  invariants:
    - id:    <slug>          # stable identifier (reported by validate + on status)
      check: <predicate>     # the predicate — SAME shape detection/gates use; True = holds
      why:   <prose>         # explanatory prose surfaced when the check fails
      applies_to: <state?>   # core (optional, COR-040)  scope to one state; ABSENT = process-wide (COR-035 unchanged)
```

- **Position-independent by default; optionally region-scoped (COR-040).** By default an invariant is checked irrespective of where the subject is — a property of *being* anywhere in the process, not of *moving*; the engine evaluates it against current reality regardless of the resolved position (an indeterminate or absent position does not stop it being checked). An invariant may carry an optional **`applies_to: <state>`** scoping it to one state — the **open-region** slot (below). The engine then **filters** the report on the resolved position: an unscoped invariant stays process-wide (COR-035 unchanged); a scoped invariant is evaluated and surfaced **only** when `resolve_position().state_id` equals its region, and is **not-applicable** (not evaluated, not surfaced) both when the subject is in another region and under an *indeterminate* position (the engine cannot confirm the region, so it never reports a spurious out-of-region violation). This is a pure position filter on the one existing report — it introduces **no** invariant→move-blocking coupling; a region's boundary is enforced by its **exit gate**, not by the invariant (COR-035's report-only posture is preserved verbatim).
- **Read-only, content-free, single-subject.** The engine *runs* each `check` through the **same predicate runner that backs detection and gates** (single-subject, threaded with the subject id) and *reports* the result with the `why` on failure; it never interprets what the invariant means and never reads across subjects (COR-032). An indeterminate `check` (error / timeout / unparseable / unresolved) is **fail-closed** — reported as NOT holding (a check that cannot be confirmed is treated as a violation, mirroring `resume_when`).
- **Report-only enforcement, surfaced on every status read.** A violation is **surfaced on the status view** (the load-bearing half — an agent reading status sees it every read, and a binding's wrapper declines downstream) and reported by the dedicated **`validate`** operation (`pkit process validate <address>` — narrative or `--json`, exits non-zero on any violation). It does **not** block moves, fail transitions, or remediate; a binding that wants a hard always-gate expresses it as a gate predicate. The status narrative shows only *violations* (to stay terse); `status --json` and `validate` carry the full set.
- **Determinism preserved.** An invariant is a predicate over reality, exactly like a detection predicate — position stays inferred and the engine stays a deterministic validator.

Per-state (`applies_to`) **scoping** now ships (COR-040) alongside the **open region** (below): a region-scoped invariant surfaces on status as the reason the region's exit gate is shut. **Boundary-enforcement** is delivered as **gate composition, not move-blocking** — the exit gate's predicate references the region's conditions — so COR-035's report-only decision is preserved verbatim (invariants report; the exit gate checks). **Deferred** (each its own future decision when a binding needs it, per COR-035): invariant **severity** / auto-remediation; and **cross-subject** always-checks (which require the breadth COR-032 holds back).

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
- an **open region** (core, COR-040) — a state (`open_region: true`) with no internal edges, bounded only by region-scoped `invariants` (`applies_to: <this state>`) + an explicit exit gate (the engine drops to a deterministic boundary check: "may this subject leave yet?"). It adds **no new node kind** and no sub-state sublanguage — genuinely-staged inner work is a *composed* process (COR-036) the exit gate reads an outcome from, not an internal edge. The engine composes it entirely from existing parts (ADR-036): region scoping is a **filter** on the invariant report keyed on the resolved position; enforcement is the **exit gate** (an ordinary `deterministic` / `authorisation-artifact` gate whose predicate references the region's conditions) — **not** a move-blocking invariant, so COR-035's report-only posture holds; a shut exit is a **closed gate** (a determinate "not yet"), and status names the unmet region-scoped invariants as the reason it is shut. A compound "(readiness predicate) AND (cross-authority sign-off)" exit is **not one gate**: the sign-off stays an `authorisation-artifact` gate the engine computes (never folded into a `deterministic` predicate, which would lose the authorship guarantee), and any hard structural AND lives in the binding's wrapper (ADR-036 §4).

In every mode the engine remains a deterministic validator. (Theory: for a finite, known block alphabet this is equivalent to a static graph; the open region is the escape hatch for genuinely open-ended work.)

## Composition — cross-process outcome resolution (core)

[COR-036](../decisions/core/COR-036-process-composition.md) un-defers the composition slot and gives the engine its one genuinely-new capability: **resolve another process's terminal outcome** and read it as an input to a parent's gate. A process exposes a public **interface** = `inputs` (what it needs to start) + `outcomes` (its named terminal states — a `terminal: true` state *is* an outcome). A parent embeds *one* inner process via a **`subprocess` state** that `runs: <capability>:<process-id>`, supplies the inner's inputs on entry, and wires the inner's outcomes to its own outgoing transitions. **All coupling lives in the parent**; the child references nothing upward, so it is reusable and parent-agnostic.

This ships the **nest/call** timing (a parent waits for an inner outcome). The **enumerate-and-fold aggregate** across many inner subjects (cascade) builds *on* this single-inner resolution as its per-subject step and ships in [COR-037](../decisions/core/COR-037-process-cascade.md) (see Cascade below). The **overflow/hand-off** timing (a terminal state spawning or unblocking a *concurrent* sibling process — altitude-2 orchestration) remains deferred.

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
process:
  interface:                       # the public embedding contract
    version:  <int>                  # optional: the interface version (COR-053 point 5) — see below
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

- **The interface version (refinement per [COR-053](../decisions/core/COR-053-connection-points.md) point 5).** An interface may carry an integer `version`: the version of the public contract, raised only when a change breaks the processes that connect to it — an additive change leaves it alone. It is distinct from the definition's own `version`, which tracks internal change under live subjects. Only validation reads it; the engine resolves outcomes live as before. A capability that offers the process under a role declares the same integer as the offered point's `schema_version` in its package metadata — `pkit validate` reports an offered point whose `schema_version` differs from the definition's `interface.version`, naming both values and both files — and a `depends_on` entry targets it with its own `version` (below).

The `status` view surfaces the embedded inner and its live-resolved outcome (narrative: an `embeds <address>` / `inner outcome: <x>` line; `--json`: a `position.subprocess` object with `{runs, outcome, indeterminate, reason, stderr_tail}`).

**Deferred** (each its own future decision when a binding needs it, per COR-036): the **overflow / hand-off** (concurrent spawn) timing and the broader **orchestration** altitude. (The **enumerate-and-fold aggregate** + **many-inner aggregate wait** across a keyed inner's subjects shipped as cascade — COR-037, below — *consuming* this single-inner resolution as its per-subject step.)

## Cascade — fold one child process's member outcomes (core)

[COR-037](../decisions/core/COR-037-process-cascade.md) un-defers the last of the substrate's breadth slots: a parent process may look across **all** the members of **one named child process** that belong to it and ask one question — "did *every* one reach outcome X?" (or "did at least N?") — then let that answer open a parent gate. This is the **one** sanctioned, tightly-bounded place where the engine reads across many subjects, crossing the line COR-032 drew (*the engine never enumerates*) **minimally**: only through one declared child relation scoped to one parent subject, and only via a capability-supplied predicate run one subject at a time. It is **not** a general re-opening of enumeration.

**Direction is child → parent, coupling in the parent** — the same discipline composition set: the parent declares the fold over one named child; the child references nothing upward and stays reusable. The fold **consumes COR-036's single-inner resolution as its per-subject step** (it never invents a rival cross-process path) — so cascade adds **breadth** across a finite member set, never **depth** (it does not recurse the members' own subprocess/cascade gates).

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
process:
  cascade:                               # the parent's child → parent fold declaration
    runs:    <capability>:<process-id>   # the one named child process whose members are folded
    members:    <predicate>              # parent-scoped candidate-member SOURCE — returns { members: ["id", ...] }
    membership: <predicate>              # per-subject "does THIS subject belong to this parent?" test
    reducer:
      op:        all | count             # all = every member reached `outcome`  |  count = at least `threshold` did
      outcome:   <child-terminal-state>  # the child OUTCOME each member is folded against
      threshold: <int>                   # required for `count`, forbidden for `all`
  states:
    - id: <waiting-state>
      meaning: <prose>
      detection: { mode: inferred, predicate: <ref> }
  subject:
    blocked: { blocked_on: awaiting-cascade-outcome }   # the aggregate wait while the fold has not opened
  transitions:
    - from: <waiting-state>
      to:   <closed>
      authorisation: agent-autonomous
      gate:
        kind: cascade-outcome            # the ENGINE folds the `cascade` declaration — no predicate, no per-gate outcome
```

- **The binding supplies the set; the engine folds.** The engine does **not** hold or discover a containment tree. It obtains the parent-scoped candidate member ids from the `members` predicate (run **once**, threaded with **this** parent subject, returning `{ members: [...] }` — read live, determinate at the instant, never a stored or open-ended global listing), then confirms each candidate with the per-subject `membership` predicate (run **one subject at a time** through the single-subject runner — "does this subject belong to this parent?"). The `members` predicate is the **candidate-set seam** — content-free and binding-supplied, mirroring how detection gets its inputs; the engine never receives or holds a global subject list.
- **Two fold operations.** `all` — every member reached the reducer's named `outcome`. `count` — at least `threshold` members reached it (a saturation floor). One enumerate-and-fold machine, two reducers. Richer reducers (ratios / weighted / custom) stay **deferred** (they land when a binding needs one).
- **Fail-closed.** Any member whose outcome is **unresolved/indeterminate** (still moving, parked, indeterminate) holds the whole fold **unresolved** — the gate stays shut, never a false "all reached X". An **indeterminate membership test** (the `membership` predicate errored / timed out for a candidate) likewise holds the whole fold **unresolved** — symmetric with an unresolved member outcome — rather than silently dropping the candidate (a dropped candidate would look like "fewer members" and could let an `all` vacuously pass); a determinate `result: false` still cleanly **excludes** a real non-member. The **empty set** (a parent with no members of that child yet) is **fail-closed too**: an `all`/`count` over zero members does **not** vacuously open the gate (a determinate "not yet", never true) — and it covers **both** "no candidates existed" and "candidates existed but none were members" (the two intentionally collapse; neither opens the gate).
- **The aggregate wait — `awaiting-cascade-outcome`.** A cascade-gated parent parks on an auto-clearing overlay reusing COR-034's model (no `resume_when` — the live fold *is* its condition), clearing the instant the fold resolves open and a legal move exists. **Acyclic by construction:** the parent waits only on its members' already-resolved **terminal** outcomes, and a terminal subject waits on nothing, so the aggregate wait cannot join a wait cycle — the deferred `deadlock` reason is safe here by construction, not by hope.
- **Read-only, deterministic, single-level.** Resolving the fold runs predicates and resolves member outcomes **live**, writing nothing; the fold is a deterministic reduction over a finite member set (P3/P6 hold — each member outcome is a composed definite answer, the membership set a live re-read of a deterministic predicate). The acyclicity guard is inherited, so a cascade whose child is the parent process is refused like a cyclic embedding.
- **Known limitation (accepted, ship-narrow).** Predicate evaluation is **not memoised across the breadth of a fold**: the `members` predicate runs through the parent runner's per-invocation cache, but each member's outcome and membership are resolved through a **fresh, uncached** runner, and within one `status` render `resolve_cascade_outcome` is invoked 2–3× (precheck gate + `position.cascade` surface + the blocked wait-reason) × N members — so member predicates re-run per call. Accepted for the narrow ship (the member sets the bindings fold are small); a shared per-render fold cache is **deferred** until a binding's set size makes it pay.

The `status` view surfaces the live fold when the current state has the cascade-gated move (narrative: a `folds <address> (<op>)` / `fold: <reached>/<total> …` line; `--json`: a `position.cascade` object with `{runs, op, outcome, threshold, reached, total, opened, indeterminate, reason, stderr_tail}`).

**Deferred** (each its own future decision when a binding needs it, per COR-037): **forward / position cascade** (bump a parent up to match its furthest child — a position reduction, not a terminal-outcome fold; pm keeps it capability-local); **richer reducers** (ratios / weighted / custom); **overflow / hand-off** (a terminal state spawning or unblocking a concurrent sibling — altitude-2 orchestration); **peer-cycle deadlock** detection and **cross-subject invariants** (different cross-subject machines, each its own slot).

## depends_on — inert cross-process connection metadata (core, COR-038)

[COR-038](../decisions/core/COR-038-process-connections.md) adds a state's `depends_on` list: a label the engine **never acts on** — pure declared metadata, shape-checked so it is uniform and machine-readable, that a future render reads to draw the project's whole configured cross-process wiring. It adds **no engine capability**.

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
states:
  - id: <state>
    depends_on:                      # core (optional, COR-038)  one entry per declared connection
      - upstream: <capability>:<id> | <publisher>::<role>:<point>   # core   by implementation (same grammar as subprocess/cascade), or by role (COR-053)
        relation: informational | gates-on-readiness | triggered-by | constrained-with   # core   CLOSED set
        mode:     pull | push        # core      pull = read on the reader's turn  |  push = mediated OUTSIDE the engine
        why:      <prose>            # core      REQUIRED reason the render surfaces
        version:  <int>              # core (optional, COR-053)  the upstream INTERFACE version targeted
        mandatory:                   # core (optional, COR-053)  the upstream must exist — read by the capability lifecycle only
          reason: <prose>            # core      REQUIRED with the mark: shown in every refusal and warning it causes
        handoff:                     # core (optional, COR-042)  OPT-IN evaluable hand-off contract — read by `health` only
          trigger:    <state>        # core      upstream state meaning "ready to hand off" (declare a STABLE state; an ephemeral trigger is an authoring smell — subjects that transit it leave the report, picked up or not)
          candidates: <predicate>    # core      binding-supplied source of upstream candidate ids (registered command; a source that can silently return nothing against a wrong root is the sibling authoring smell)
          resolve:    <predicate>    # core      binding-supplied: upstream id → downstream id(s) | explicit absence; error = indeterminate (fail-closed)
```

- **Inert by default — never read by the runtime; each other reader bounded to one purpose (re-scoped by [COR-042](../decisions/core/COR-042-process-health.md), then [COR-053](../decisions/core/COR-053-connection-points.md) point 6).** The engine's runtime operations (`status`, `can-move`, `move`, `validate`-of-position) and **every gate never read `depends_on`** — the engine module names neither the field nor the mark, a structure a test pins. Its readers are the **schema** (shape-validates it: well-formed `upstream` address, `relation`/`mode` from their closed sets, `why` present, a `mandatory` mark only with a reason), the **render** (out-of-engine, declarations only), the **`health` surface** (out-of-runtime, report-only) for entries carrying the **opt-in `handoff` contract** and nothing else, and the **capability lifecycle** — install, upgrade, uninstall — which reads the **`mandatory` mark alone**, from the generated package copy (below), only to check that the upstream definition exists. Entries without a contract or a mark are never evaluated by anything, one level *more* inert than COR-035's invariants. A **malformed entry stays a lint error at authoring time** (`schemas validate`), **never a fail-closed gate** — it cannot affect whether any subject may move; a contract that cannot be *interpreted* at health time (unresolvable upstream address, phantom trigger state) is reported **indeterminate**, never silently green (COR-042).
- **Addressing an upstream by role ([COR-053](../decisions/core/COR-053-connection-points.md) point 2).** `upstream` takes one of two forms. The **implementation form** `<capability>:<process-id>` names one capability's definition. The **role form** `<publisher>::<role>:<point>` names a process **offered** under a role — a capability declares the role among its `connections.roles` and the process under `extension-points.offers` in its package metadata (the lifecycle README, "The connection, documentation and friction blocks") — and it reaches whichever installed capability is that role's **active provider**. So replacing that capability with another providing the same role touches nothing in this definition. The role form is scoped to `depends_on`: embedding (`subprocess`, `cascade`) stays implementation-addressed, because a role there would make the engine consult the wiring. Existing definitions keep working unchanged; the implementation form stays valid. An entry may name the upstream **interface `version`** it targets (Composition, "The interface version"): it then connects only to an offered process at an equal version, and another version leaves it inert. Where a hand-off contract sits on a role-addressed entry, `health` reads the process the role's active provider offers there from the wiring resolver — never a resolution of its own — and an address no active provider offers (no provider installed, providers in conflict, or no process at that address) is **indeterminate**. `pkit process hand-off` reads the same process when it stamps the contract, and checks the trigger against its states; a role address that reaches no offered process is a warning there, since the trigger cannot be checked. The `candidates` seam still receives the address as declared.
- **The mandatory mark ([COR-053](../decisions/core/COR-053-connection-points.md) point 6).** A connection is optional unless its entry says, with a `reason`, that it is mandatory: `mandatory: { reason: <prose> }`. The mark without a reason is refused. It means the upstream process definition must exist — at a compatible interface version when the entry names one. It is read by the capability lifecycle and by nothing else, with the direction split capability dependencies use ([COR-030](../decisions/core/COR-030-capability-dependencies.md)): installing, registering or upgrading the capability **carrying** the mark is **refused** while the upstream is missing or incompatible, the reason quoted; upgrading or uninstalling the capability it **targets** is **warned**, each counterpart named, and proceeds only under `--force` — never a hard block, so no deadlock. `pkit validate` reports an unmet mark as an error on the carrier's package, and two marks facing each other as a cycle no install order could satisfy. The CLI reference, "Capabilities", carries the refusal and warning wording.
- **The generated `depends-on` list ([COR-053](../decisions/core/COR-053-connection-points.md) point 4).** The capability's package metadata carries the same connections as one list, `connections.extensions.depends-on`, so a reader — and a plan for a capability not yet installed — sees them without opening a definition, and so the lifecycle reads the marks without parsing definitions. The definitions are its **single source**: `pkit capabilities refresh <capability>` regenerates it and marks it `generated: true` — one entry per distinct upstream and targeted version, sorted, carrying `process`, `schema_version` (the entry's `version`) and the `mandatory` mark when any declaring entry carries one. **Never hand-write it.** `pkit validate` fails a copy that differs from what the definitions generate, naming the refresh as the fix, and the definition always wins. Refresh is an **authoring-time** command, run where the capability is authored — after `pkit process couple`, or whenever a definition's `depends_on` changes. In an adopting project a kit-shipped capability's package file is core-owned: refresh refuses there, and a stale copy is the capability author's to fix.
- **Stamping a coupling ([COR-044](../decisions/core/COR-044-process-authoring-layer.md)).** Author an entry with `pkit process couple` rather than by hand. It takes the upstream in either form — `--upstream <capability>:<process-id>`, or by role `--upstream <publisher>::<role>:<point>` — plus the targeted interface version as `--version <n>` and the mandatory mark as `--mandatory <reason>`, and writes each only when given, so the entry has the shape above. A role address is resolved through the wiring, as `health` resolves it; one that reaches no offered process is warned about, not refused, since the entry is inert. The stamp writes the definition and nothing else: when the capability's generated `depends-on` list is now stale, it ends by naming `pkit capabilities refresh <capability>`. **Run it** — `pkit validate` fails until the list follows the definitions. The CLI reference, "`process couple`", carries the grammar.
- **The `relation` set annotates only the edges the engine cannot already see.** `informational` (advisory, no runtime effect); `gates-on-readiness` (names the cross-process edge an opaque gate predicate enforces but declares nowhere); `triggered-by` (an externally / connector-mediated coupling the engine never sees — pairs with `mode: push`); `constrained-with` (a cross-subject invariant named for visibility — the slot's **first family**, hand-off existence, ships *checking-not-enforcing* via COR-042's contract, orthogonally to `relation`; enforcement stays deferred).
- **The seam payloads (ADR-048).** Both contract predicates are commands the *declaring* (downstream) capability registers, run through the ordinary predicate-runner contract (one subject positional + `--json`, cwd = repo root, read-only). `candidates` runs with the subject slot carrying the contract's **upstream process address** (the scope it enumerates; the trigger is statically known to the binding from its own declaration) and returns `{candidates: ["<id>", …]}` — the source *proposes*, and `health` confirms each id one subject at a time through the engine's per-subject position resolution. `resolve` runs once per confirmed subject with the subject slot carrying that **upstream subject id** and returns `{downstream: ["<id>", …]}` — non-empty = satisfied (fan-out allowed), explicitly empty = determinate absence (a **missed** hand-off), error / no explicit list = indeterminate (fail-closed).
- **Derive-don't-annotate — `composed-subprocess` / `aggregates` are deliberately NOT relation values.** A composition / aggregation edge is already fully declared by the `subprocess` / `cascade` block the engine owns and resolves; re-stating it as an annotation would be a second copy of a fact whose primary home is that block, and the two **will drift** (single source of truth — COR-006). So the render computes the configured composite as **derived edges** (read from `subprocess` / `cascade`) **∪ annotated edges** (`depends_on`) — every edge expressible exactly one way, no edge both. `depends_on` is precisely *the visibility layer for the edges the engine cannot see.*
- **`mode: push` introduces no eventing.** The position engine stays **pull-only** (COR-038 point 3): `push` means only "this edge is mediated outside the engine"; the engine never pulls it and records it solely for visibility. No subject is created, advanced, or notified by a fired event inside the engine.

**The render.** `pkit process graph` draws the configured composite (derived ∪ annotated edges, each labelled with its relation and mode). It is the process view of the one wiring graph ([COR-053](../decisions/core/COR-053-connection-points.md) point 7, `pkit connections graph`), which adds the offered-process edges through which a role-addressed `depends_on` reaches the process answering it; the CLI reference's "Connections commands" specifies both.

**Deferred** (per COR-038). The cross-subject always-check slot's **first family** (missed-hand-off existence, report-only) shipped via [COR-042](../decisions/core/COR-042-process-health.md); still deferred from that family, each on a real demand: general cross-subject invariants (mutual exclusion and friends), the data-coupling drift/diff signals, the orphan-artifact inverse, the trigger state-set / at-or-beyond form, auto-remediation, and any **enforcing** coupling (supersession weight per COR-042).

## The engine

The backbone exposes the engine as a `pkit process …` surface. The core operations:

| Operation | Answers / does |
|---|---|
| `status` | where the subject is · why · how it got here (the journal, or "journal logging is not enabled for this project") · legal moves with live prechecks · next hint — narrative or `--json` (which carries `journal_logging: {enabled, committed}` beside `journal`) |
| `can-move <to>` | validate a candidate move (gate precheck + authorisation); refuse with a self-explaining reason |
| `move <to> [--from <state>]` | execute a legal move; record the journal entry where the project keeps a journal (and run hooks, deferred) — the verdict is the same either way. `--from` names the state the subject held before the caller applied the move's domain side-effect; the move is validated and journaled from there (the seam-ordering contract below) |
| `validate` | run the subject's invariants (COR-035) and report which hold / are violated — narrative or `--json`; exits non-zero on any violation |
| `health` | walk every declared hand-off contract (COR-042) and report missed hand-offs — upstream subjects at their trigger with no downstream counterpart; takes **no subject**; out-of-runtime, report-only, deterministic; narrative or `--json`; exits non-zero on any miss **or indeterminate** |

The engine is **content-free**: it reads any capability's process definition + that subject's reality and resolves/validates against it. Capability commands (the discipline's verb-subject wrappers) supply the definition + subject + any domain side-effects and delegate the state-machine mechanics to the engine.

**Code home (ADR-020).** The engine ships in the `pkit` binary (`src/project_kit/process.py`), invoked only as `pkit process …`; the engine *code* is not propagated to adopters (only this spec, the shape contract, and the journal home are). Capability wrappers call the engine by **subprocess**, never by import.

### The predicate runner (engine contract)

A predicate's `run:` resolves to a command the owning capability **registers** in its `package.yaml` — a leaf of its `commands:` tree, named by the leaf's own name — not a raw path or shell string; the engine rejects an unregistered name with a self-explaining error. The engine runs the resolved script through the backbone's **one command runner**, the lookup and bounded run it shares with the validator registry's query runner (the lifecycle README, "How a registered command is run"; ADR-057 point 5), under the **predicate policy**: explicit argv — the subject + `--json` — with the working directory at the repo root and the environment unchanged but for the run's deadline, since a predicate may reach the network (no offline marker is set); in its own process group, bounded by the backbone's thirty-second command bound, and overrunning kills the whole group, so the interpreter a `uv run --script` shebang starts as a grandchild stops too — inside another run, by the time that run has left and in the outermost run's group (the lifecycle README, "A run inside a run"). The engine reads one JSON object from standard output, and:

- **deterministic gate / detection** → uses the predicate's `result`;
- **authorisation-artifact gate** → reads `{ exists, produced_by }` and computes `result = exists && produced_by != actor` *itself* — the engine enforces cross-authority and **ignores any `result` the predicate supplies** (non-overridable).

Predicates **must be read-only** — `status` runs them live, so a mutating predicate would be a side-effect bug.

**Failure is fail-closed.** A predicate that errors, times out, returns unparseable JSON or anything but a JSON object, or doesn't resolve is **indeterminate**: `status` shows it distinctly ("couldn't evaluate: …") and `move` refuses. An unrecognised or schema-future gate (engine/definition version skew) likewise fails closed — never a silent pass. Gates are correctness boundaries (unlike the permission hook's fail-open *availability* posture).

**An indeterminate predicate says why.** The reason names the predicate and how its run ended — `it exited 2`, `it was ended by signal 9`, `it did not answer within 30 s and was stopped`, `it could not start: …`, `it printed no JSON document on its standard output`, `it answered with JSON that is not an object`. What the predicate wrote on **standard error** — its diagnostics channel, never read as an answer — is shown beside that reason, attributed to it: in the narrative views (`status`, `validate`, `cascade`) and in a refusal (`can-move`, `move`) under a `the predicate said:` line, and in the `--json` views as a **`stderr_tail`** field of its own beside `reason` (null when there is nothing to show), never folded into a reason a consumer may match on. `status --json` also lists the detections behind an indeterminate position under `position.unevaluated` (`{state, reason, stderr_tail}`). What is shown is only the stream's **tail**: its last 10 non-blank lines and at most 1500 bytes of them, starting with `…` when cut; decoded with replacement, so a binary stream cannot fail the read; with every terminal escape sequence removed and every other control or format character dropped, so a predicate can neither flood nor rewrite the operator's terminal. So a predicate that refuses for a reason the operator can fix — a capability's prerequisite gate naming the command that fixes it — should say so on standard error: that is the message that reaches them. None of this changes a verdict: an unevaluable predicate is indeterminate, whatever it said.

**Performance.** Resolve position first (run detection predicates), then precheck only the transitions *out of* the current state; evaluate each predicate at most once per `(command, args)` per invocation. No cross-invocation position caching — that is the deferred `stored` detection mode.

### Seam-ordering contract (journal-as-intent-log)

This is canonical guidance for **all** bindings — how a capability wrapper sequences its own domain side-effect against the engine's journal write.

The journal is an **intent log, not the source of truth**. Live detection is authoritative (COR-033 P3): a subject's position is always re-derived by running the detection predicates against current reality, never read back from the journal. So the journal entry the engine appends on a legal `move` records *that a move was taken*, but the next `status` reports the *real* inferred position regardless of what the journal says. The ordering below is the same whether or not the project keeps a journal; with logging off, step 3 validates the move and records nothing.

The ordering a wrapper follows:

1. The wrapper reads the subject's position from the engine (`status --json`): the move's origin.
2. The wrapper validates and applies its **domain side-effect** (create the branch, open the PR, edit the label/board) — the change that will make live detection report the new state.
3. The wrapper calls `pkit process move --to <target> --from <origin>` (by subprocess) to **journal** the move where a journal is kept.

**Why `--from`.** After step 2 live detection already reports the target. An engine that took the live position for the origin would be asked for a move from the target to itself: refused where the definition declares no such transition, and journaled as the wrong transition where it declares one (a self-loop). With `--from` the engine validates and journals the transition from the stated origin. The engine bounds the stated origin by reality: it accepts it only while live detection places the subject at that origin (the side-effect is not visible yet) or at the target, and refuses otherwise. When the subject already shows the target, the origin is taken on the wrapper's word — bounded by the present, not verified — and it selects the transition whose gate the engine evaluates. Gates are evaluated against reality *after* the side-effect, so a gate the move's own side-effect would flip is one the wrapper checks (`can-move`) before it writes. Side-effect first with `--from` is the canonical order. A wrapper that journals before applying its side-effect omits `--from`, and the move starts at the live position — at the cost that an entry can exist for a side-effect that never landed.

Because detection is authoritative, the seam is self-correcting whichever step fails. Under the canonical order, a journal write that fails after the side-effect leaves the journal one move short, which the wrapper reports. Under journal-first, a side-effect that fails (or partially fails) *after* the entry was written leaves an entry for a move that never landed. Either way the next `status` runs detection live and reflects the subject's **real** inferred position — a journal entry does not say where the subject is, it only records the attempt. A wrapper should still surface side-effect failures to its caller; the point is that a failed side-effect cannot corrupt the engine's notion of position. Wrappers must **read position from the engine** (`status --json`) rather than re-inferring it themselves, so there is one source of position truth.

### The journal — optional audit (COR-033 point 7)

The engine can keep an append-only, per-subject journal of the moves it executes and of each wait's enter and resume. It is **audit, not runtime**: position, gates, invariants and the blocked overlay never read it, so every answer the engine gives is the same with it on or off. Keeping it is the project's choice, declared in the backbone configuration file, `.pkit/project/config.yaml` (the CLI reference, "Configuration file"):

```yaml
process:
  journal:
    enabled: false    # default — keep no journal
    committed: false  # default — when kept, keep it per clone
```

| Mode | Setting | What the engine does | Journal files in version control | Who can rely on it |
|---|---|---|---|---|
| **Off** (default) | `enabled: false`, or no `process` block | writes and reads no journal; `status` says "journal logging is not enabled for this project"; a wait has no `since` | ignored, so a stray file is never committed | nobody — the audit trail is whatever the binding names instead (project-management: the tracker's timeline plus pkit's audit comments) |
| **Clone-local** | `enabled: true`, `committed: false` | appends an entry per move and per wait event; `status` shows how the subject got here | ignored: each clone keeps its own, absent from pull requests and lost with the clone | the clone that made the moves |
| **Committed** | `enabled: true`, `committed: true` | the same | not ignored: commit them with the work that moved the subject | everyone — shared, reviewable, durable |

- **Turning it on.** `pkit config set process.journal.enabled true --yes`, and `pkit config set process.journal.committed true --yes` to commit the journals. Logging starts then; nothing is back-filled.
- **The ignore rules follow the setting.** The backbone contributes the journal pattern (`.pkit/capabilities/*/project/process/**/*.journal.jsonl`) to the rendered `.pkit/.gitignore` — never your root `.gitignore` (ADR-009) — unless the setting is `committed: true` with `enabled: true`. `pkit config set` re-renders the file at once; a hand edit of the configuration takes effect at the next `pkit sync`. A journal already tracked by git stays tracked whatever the file says. A capability that still declares the pattern in its own `runtime_ignore` — one older than the backbone that took the line over — cannot keep committed journals ignored: while they are committed the render leaves its entry out and names it in a comment line (`# dropped: <capability> '<entry>' — the backbone owns the journal pattern while journals are committed`), and `pkit config set` reports it. `pkit validate` warns on the entry then (the lifecycle README, "Validation: the package schema") and names the cure for where the package comes from: upgrade a methodology-shipped capability together with the backbone, move an externally sourced one's pin to a release that drops the entry, or drop the entry from your own. While the journals stay ignored the entry is redundant and renders as declared, without a warning.
- **Turning it off** leaves existing journal files where they are; the engine stops reading and extending them.
- **Where journals live.** In the owning capability's adopter-owned `project/process/` subtree (see Layout). Uninstalling a methodology-shipped capability deletes its directory, journals included; committed journals survive in version-control history.
- **Upgrading.** The upgrade that introduced the setting keeps logging on for a project it finds keeping journals — `enabled: true`, with `committed` following whether those journals are tracked by git — and writes nothing otherwise, so logging stays off (the backbone migration `1.150.0/001-keep-process-journal-logging.sh`). It decides from the clone it runs in: a project whose journals lived only in other clones turns logging on itself.

## Binding a process (how a capability uses this)

1. Author a process definition as the capability's own instance schema at `.pkit/capabilities/<capability>/schemas/<process>.yaml`, declaring conformance to the shape contract (`../../../schemas/_defs/process.schema.json`). **Author it through the authoring layer below, not by hand** — the stamps own the file's correctness.
2. Drive it through the capability's verb-subject commands, which call the engine.
3. The process is addressable elsewhere as `<capability>:<process-id>` — a parent embeds it by that address through a `subprocess` state (composition, COR-036). When its capability offers it under a role, another definition's `depends_on` may address it by role instead (`<publisher>::<role>:<point>`, COR-053). Orchestration (concurrent hand-off) remains deferred.
4. When a definition's `depends_on` changes, run `pkit capabilities refresh <capability>` so the generated `depends-on` list in the package follows it (see depends_on above); `pkit validate` fails until it does.

The existing schema-binding grammar (COR-023) is unchanged; capabilities stay independent, self-describing peers.

## The authoring layer

Authoring a definition does not mean knowing this document by heart. Per [COR-044](../decisions/core/COR-044-process-authoring-layer.md) the layer has three tiers, split by what kind of work each does:

- **Commands** — `pkit process new` / `couple` / `hand-off`. Deterministic stamps: they scaffold and mutate the definition, validate every value against the vocabularies **read as data from the shape contract** (`../schemas/_defs/process.schema.json`), scaffold a fail-closed predicate stub for each declared evaluable, and register it in the owning capability's package. All three require an owning capability the project **registers as a component** — the same set contract discovery walks — so a stamp can never write a definition nothing watches; the CLI reference specifies the grammar and that refusal. `health --interpretation-only` is the read-only completion check that pairs with them.
- **The `process` skill** — the walkthrough over those commands: it asks the shape questions (what is the subject, what does each state *mean*, which moves are gated, is this trigger stable, would this candidate source fail loudly or return empty), then stamps the answer. It also owns the judgment the stamps deliberately refuse — routing an adopter with no owning capability through capability authoring first.
- **The `process-author` agent** — the **teeth**: the predicates behind every evaluable the shape declares (detections, gates, entry guards, `resume_when`, invariant checks, both hand-off seams). It turns the owner's plain-language intent into predicates satisfying the **predicate-runner contract above** — read-only, fail-closed, answering about the one subject it was given — and finishes with `health --interpretation-only`. Shape problems it uncovers route back through the skill's operations rather than being fixed by hand, and predicate registration stays with the commands. Stubs fail closed until implemented, so an unwritten predicate reads as indeterminate rather than green.

  **Its write authority is yours to grant.** Per [ADR-051](../../tech-docs/architecture/decisions/ADR-051-process-author-edit-authority.md) the agent owns exactly one overlay category, `process-authoring-targets` in `.pkit/agents/project/overlay.yaml`, which ships as an explicit empty list: the agent deploys owning nothing until you list your own definition files and predicate-script locations there, at file granularity. No entry may resolve into sync-managed content — the deploy refuses it and names the path — so a methodology-shipped definition can never enter the grant. The agents area README specifies the category; single-definition-per-invocation scoping is body discipline, not metadata.

The split is the point: a definition's *shape* is declarative data with closed vocabularies, so procedure can walk it; its *teeth* are domain logic over the owner's reality, which is authoring judgment.

**Deferred authoring operations** (this list is authoritative; the skill points here):

- `amend` — evolving states or transitions under live subjects, riding the definition `version`. Also the repair path for a mis-declared coupling or contract.
- Adding a **wait** (COR-034) or an **invariant** (COR-035) to an *existing* definition. A fresh definition declares both through `new`.
- **Subprocess embedding, cascade folds, open regions** — the three *structural composition* blocks. No stamp surface in **any** definition, fresh or not (COR-044 point 3 as amended for #716); each lands when a real authoring case demands it. The deferral is **authoring-only**: the substrate resolves all three at runtime today, so a definition carrying one behaves exactly as this spec describes — what is missing is the flag grammar to stamp it.

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
                                    # per-subject journal — append-only JSONL, written only when the
                                    # project enables journal logging; committed or git-ignored per
                                    # `process.journal.committed`; in the capability's adopter-owned
                                    # project/ subtree (sync-safe; the engine owns the path and the
                                    # backbone its ignore pattern — capabilities don't declare it)
```

The engine ships as a backbone CLI surface (`pkit process …`) homed in the binary per ADR-020 — capabilities never re-implement the state machine, they bind to it. The journal, where kept, is project-owned data, committed or clone-local as the project chose.

## Grounding & status

Per COR-033's acceptance-gate (COR-007 grounding), the substrate ships proven against two instances: the project-management process **rebound** onto it (its breadth / closure / PR-sub-lifecycle fields kept capability-local), and one new concrete binding as the grounded second instance. Each binding is its own capability decision (DEC); the pm rebind carries a COR-010 migration. The deferred extension points each become real — and gain their own decision — when a binding first needs one.
