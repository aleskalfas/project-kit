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
      depends_on:                   # core (optional, COR-038)  INERT cross-process connection metadata — engine NEVER evaluates it
        - upstream: <capability>:<id>   # core   the upstream process address (same grammar as subprocess/cascade)
          relation: informational | gates-on-readiness | triggered-by | constrained-with   # core   CLOSED set (no composed-subprocess/aggregates — those are DERIVED)
          mode:     pull | push     # core      pull = read on the reader's turn  |  push = mediated OUTSIDE the engine (no eventing)
          why:      <prose>         # core      REQUIRED reason the render surfaces
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
    inputs:   [{ name, meaning?, required? }]   # core      what the inner needs to start
    outcomes: [{ name, meaning? }]              # core      named terminal states a parent may wire
  orchestration: { overflow, cross_gates }   # deferred  altitude-2 (overflow / hand-off — concurrent spawn)
```

### Subject cardinality (core)

A process declares `subject.cardinality`:

- **`singleton`** — one journey per process. No subject identifier; the engine tracks the single journey under a fixed internal key.
- **`keyed`** (COR-032) — many units under one definition, each at its own position (e.g. one per issue). The engine operates **per a supplied subject identifier**: it resolves *that* subject's position, validates and executes *its* moves, and writes *its* journal, threading the identifier through every predicate it runs (as the predicate's first argv). The identifier is **required** for a keyed process — there is no singleton default; `pkit process … --subject <id>` must be given, and the engine errors clearly if it is missing. A keyed subject may declare a descriptive `key` naming what identifies a unit (e.g. `issue-number`); the engine does not interpret it, but subject identifiers must be safe to use in the per-subject journal path.

The engine **never enumerates** a keyed process's subjects — it only ever acts on the one it is given. The **one** sanctioned, bounded exception is the **cascade fold** (COR-037, below): a parent reads across the members of *one declared child process* scoped to one parent subject, and only through a capability-supplied membership predicate run one subject at a time — never a containment tree the engine holds, never a general subject-listing API. Everywhere else the never-enumerate discipline is unchanged; pm's *forward* (position) cascade stays capability-local until a binding demands the shared form.

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

- **`blocked_on` ships four reasons.** Three are establishable from *one* subject's reality (COR-032): **`awaiting-human`** (a person must act), **`awaiting-condition`** (an external fact must become true), and **`awaiting-subprocess-outcome`** (COR-036, single-inner: the subject is parked in a `subprocess` state whose embedded inner has not yet reached a wired terminal outcome — see Composition below). The fourth, **`awaiting-cascade-outcome`** (COR-037), is the single sanctioned *cross-subject* fold wait: the subject is parked at a state whose outgoing `cascade-outcome` gate folds across one declared child process's members and has not yet resolved open (see Cascade below). The enum stays open to additive widening — the remaining cross-subject reason `deadlock` (a peer-subject cycle) joins it where the engine reads across a crowd of subjects in a *waiting* posture (deferred; the cascade fold is acyclic by construction — it waits only on members' already-resolved terminal outcomes).
- **The blocked flag is a DERIVED overlay, recomputed live — never stored truth. Resume differs by reason** (COR-034):
  - **`awaiting-human`** carries **no `resume_when`** (the schema forbids one). It is *currently* blocked while the subject sits at a non-terminal position with an outgoing, **not-yet-taken** `user` move — whether that move's gate is open (ready to take) or closed (the human must intervene in reality first). The **resume is the person taking the move** — the position advancing off the parked state, which removes the pending move. The engine consults **no side-predicate**: a side-fact existing (e.g. a review file) must **not** clear an "approve?" block — only taking the move does. (Tying the resume to a side-predicate is forbidden precisely because the two can disagree: a satisfied side-fact while the move is still gate-closed would falsely report "not waiting" on a subject that is genuinely stuck.)
  - **`awaiting-condition`** carries a **required `resume_when`** predicate. It is *currently* blocked when (a) it has **no legal move** (the shipped "no legal move" detection — a non-terminal, determinate position out of which no transition is allowed), and (b) its `resume_when` predicate does **not** yet hold. When `resume_when` holds, the engine **auto-clears** the flag — the external fact turning true with no human in the loop. An indeterminate `resume_when` is fail-closed (the subject stays blocked rather than silently resuming).
  - **`awaiting-subprocess-outcome`** (COR-036, single-inner) carries **no `resume_when`** (the schema forbids one, like `awaiting-human`). It is *currently* blocked while the subject sits in a `subprocess` state with **no legal move** — i.e. no `subprocess-outcome` gate currently passes, because the embedded inner process has not reached a *wired* terminal outcome. It is **auto-clearing** like `awaiting-condition`, but the "condition" *is* the recursive resolution carried by the `subprocess-outcome` gates (re-evaluated live in the "no legal move" check) — when a wired inner outcome resolves, a gate opens, a legal move exists, and the wait clears with no human in the loop. A parent parked on an **unwired** inner outcome stays correctly blocked (the author owns outcome→transition wiring, not the engine).
  - **`awaiting-cascade-outcome`** (COR-037, the aggregate fold wait) carries **no `resume_when`** (the schema forbids one, like `awaiting-subprocess-outcome`). It is *currently* blocked while the subject sits at a state whose outgoing `cascade-outcome` gate has **no legal move** — i.e. the fold over the declared child's members has not resolved open. It is **auto-clearing**, the "condition" being the live fold itself (re-evaluated live in the "no legal move" check) — when the fold resolves open (all members reached the outcome, or the threshold is met), the gate opens, a legal move exists, and the wait clears with no human in the loop. Fail-closed throughout: any unresolved member, and the empty member set, hold the fold shut (the parent stays correctly blocked).
- **The wait is journaled on enter and on resume.** Entering a blocked position appends a `blocked-enter` event; clearing it appends a `blocked-resume` event (each a journal entry — there is *no* separate emission/dispatch channel; the deferred **hooks** slot will react to these journaled transitions when it ships). `since` (the wait's age) is read from the open `blocked-enter` entry; `assignee` is carried from the declaration. **The journal is the audit trail; the CURRENT blocked-ness is always the live evaluation** (for `awaiting-human`, whether the pending move has been taken; for `awaiting-condition`, the `resume_when` predicate), **authoritative over any journal entry** (inheriting the journal-is-intent-log / live-detection-authoritative contract below).
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

The `status` view surfaces the live fold when the current state has the cascade-gated move (narrative: a `folds <address> (<op>)` / `fold: <reached>/<total> …` line; `--json`: a `position.cascade` object with `{runs, op, outcome, threshold, reached, total, opened, indeterminate, reason}`).

**Deferred** (each its own future decision when a binding needs it, per COR-037): **forward / position cascade** (bump a parent up to match its furthest child — a position reduction, not a terminal-outcome fold; pm keeps it capability-local); **richer reducers** (ratios / weighted / custom); **overflow / hand-off** (a terminal state spawning or unblocking a concurrent sibling — altitude-2 orchestration); **peer-cycle deadlock** detection and **cross-subject invariants** (different cross-subject machines, each its own slot).

## depends_on — inert cross-process connection metadata (core, COR-038)

[COR-038](../decisions/core/COR-038-process-connections.md) adds a state's `depends_on` list: a label the engine **never acts on** — pure declared metadata, shape-checked so it is uniform and machine-readable, that a future render reads to draw the project's whole configured cross-process wiring. It adds **no engine capability**.

**Authored** (additive — absent on every existing process, which validate byte-unchanged):

```
states:
  - id: <state>
    depends_on:                      # core (optional, COR-038)  one entry per declared connection
      - upstream: <capability>:<id>  # core      the upstream process address (same grammar as subprocess/cascade)
        relation: informational | gates-on-readiness | triggered-by | constrained-with   # core   CLOSED set
        mode:     pull | push        # core      pull = read on the reader's turn  |  push = mediated OUTSIDE the engine
        why:      <prose>            # core      REQUIRED reason the render surfaces
```

- **Inert by design — the first declaration the engine never *evaluates*.** The engine's runtime operations (`status`, `can-move`, `move`, `validate`-of-position) **never read `depends_on`**. Its only two readers are static or out-of-engine: the **schema** shape-validates it (well-formed `upstream` address, `relation`/`mode` from their closed sets, `why` present), and a future **render** (a tool outside the engine) reads it to draw the topology. This is one level *more* inert than COR-035's invariants, which the engine *does* evaluate (and surfaces on `status`) — `depends_on` it does not evaluate **at all**. Because the engine never evaluates it, a **malformed entry is a lint error at authoring time** (`schemas validate`), **never a fail-closed gate** — it cannot affect whether any subject may move.
- **The `relation` set annotates only the edges the engine cannot already see.** `informational` (advisory, no runtime effect); `gates-on-readiness` (names the cross-process edge an opaque gate predicate enforces but declares nowhere); `triggered-by` (an externally / connector-mediated coupling the engine never sees — pairs with `mode: push`); `constrained-with` (a cross-subject invariant named now for visibility, enforcement deferred behind COR-035's cross-subject-invariants slot).
- **Derive-don't-annotate — `composed-subprocess` / `aggregates` are deliberately NOT relation values.** A composition / aggregation edge is already fully declared by the `subprocess` / `cascade` block the engine owns and resolves; re-stating it as an annotation would be a second copy of a fact whose primary home is that block, and the two **will drift** (single source of truth — COR-006). So the render computes the configured composite as **derived edges** (read from `subprocess` / `cascade`) **∪ annotated edges** (`depends_on`) — every edge expressible exactly one way, no edge both. `depends_on` is precisely *the visibility layer for the edges the engine cannot see.*
- **`mode: push` introduces no eventing.** The position engine stays **pull-only** (COR-038 point 3): `push` means only "this edge is mediated outside the engine"; the engine never pulls it and records it solely for visibility. No subject is created, advanced, or notified by a fired event inside the engine.

**Deferred** (its own future decision when a consumer exists, per COR-038): the **`pkit process graph` render** that draws the configured composite (derived ∪ annotated edges, each labelled with its relation and mode) — named now, built when it has a consumer (ship-narrow, COR-016). Enforcement of `constrained-with` waits on COR-035's deferred cross-subject invariants slot.

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
