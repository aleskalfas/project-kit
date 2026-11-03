---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/process.py
        - src/project_kit/validators.py
        - .pkit/schemas/_defs/process.schema.json
      record: [COR-032, COR-033, COR-034, COR-035, COR-036, COR-037, COR-038, COR-040, COR-042, COR-053, "ADR-023#1", ADR-036, ADR-062]
---

# The shape

What a process definition declares, field by field, and how the engine reads each part ([COR-033](../decisions/core/COR-033-process-substrate.md)). The shape contract, `.pkit/schemas/_defs/process.schema.json`, states the same fields as a schema, and every definition conforms to it.

## Contents

<!-- pkit:contents -->
- [Core and deferred](#core-and-deferred)
- [The fields](#the-fields)
- [Subject cardinality (core)](#subject-cardinality-core)
- [Detection modes (core)](#detection-modes-core)
- [Blocked — a first-class wait (core)](#blocked--a-first-class-wait-core)
- [Invariants — position-independent always-checks (core)](#invariants--position-independent-always-checks-core)
- [Determinism across dynamic structure](#determinism-across-dynamic-structure)
<!-- /pkit:contents -->

## Core and deferred

Each field of the shape is marked core or deferred ([COR-033](../decisions/core/COR-033-process-substrate.md) point 5).

- **Core:** shipped, and read by the engine.
- **Deferred:** a named extension point, designed into the shape now. The engine builds it only when a real binding needs it, and it then gains a decision of its own.

## The fields

A process definition, which a capability authors, declares the fields below. Each line notes whether it is core or deferred.

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
      resume_when: <predicate>      # core      REQUIRED for awaiting-condition, FORBIDDEN for the other three; re-evaluated LIVE, auto-clears the flag when it holds
      assignee:    <owner?>         # core      optional: who owns the wait (audit colour)

  states:
    - id:      <slug>               # core
      meaning: <prose>              # core      load-bearing: the status view renders from it
      detection:
        mode:      inferred | classified   # core: inferred — the predicate answers "is the subject in this state?"; classified — "which state is the subject in?"; both read reality live; ONE mode for every state of a definition  |  deferred: stored | hybrid
        predicate: <ref>            # core      a checkable predicate (classified: the states naming one command + `with` share its one answer — see "Detection modes")
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
          handoff: { trigger, candidates, resolve }   # core (optional, COR-042)  OPT-IN evaluable hand-off contract — read by `health` only
      entry:    true | { when: <predicate> }   # core   start state: unconditional, or guarded; MULTIPLE entries allowed
      terminal: <bool>             # core      end state? (also a process OUTCOME for composition — COR-036)
      open_region: <bool>          # core (optional, COR-040)  free-order state: no internal edges, bounded by region-scoped invariants + one exit gate

  transitions:
    - from: <state> | "*"          # core      back-edges + self-loops expressible
      to:   <state>                # core: static target  |  deferred: a resolver(data) over a known block set
      trigger:       <command>     # core      the named action
      authorisation: user | agent-autonomous | script   # core   WHO may move — the CALLER enforces it; the engine reads it only for an awaiting-human wait
      gate:                        # core      WHAT must hold — must be checkable (the README, "Gate-checkability")
        kind: deterministic | authorisation-artifact | subprocess-outcome | cascade-outcome   # core: subprocess-outcome (COR-036) — engine-computed from an embedded inner outcome; cascade-outcome (COR-037) — engine-computed from the process's `cascade` fold
        predicate: <predicate>     # core      REQUIRED for deterministic and authorisation-artifact; FORBIDDEN for the two engine-computed kinds
        outcome: <inner-state>     # core (subprocess-outcome)  the inner OUTCOME this move leaves the subprocess state on
      severity:      <ref>         # core      a validation-severity token (reused, not re-invented)
      why:           <prose>       # core      status view
      hint:          <command>     # core      what to run next
      prompt:        <question>    # core (optional, COR-034)  the QUESTION posed on an awaiting-human move (user-auth only)
      hooks: [...]                 # deferred  on-move actions (integral | reactive)

  cascade:                         # core (optional, COR-037)  fold ONE child process's member outcomes into a gate
    runs:    <capability>:<id>     # core      the one named child process whose members are folded
    members:    <predicate>        # core      parent-scoped candidate-member SOURCE (returns { members: [...] }); the engine never enumerates the child's subjects
    membership: <predicate>        # core      per-candidate re-confirm, given the candidate alone and never the parent: it can be read, and is still a member (run one at a time)
    reducer:
      op:        all | count       # core      all = every member reached `outcome`  |  count = at least `threshold` did
      outcome:   <child-state>     # core      the child OUTCOME each member is folded against
      threshold: <int>             # core (count)  the saturation floor (forbidden for `all`)
    on_empty:  fail-closed | satisfied   # core (optional, COR-037)  a DETERMINATELY empty member set: gate shut (default) or open
  # the parent gate it feeds is a transition `gate: { kind: cascade-outcome }` (no predicate / outcome — the fold IS the check)

  invariants:                      # core (optional, COR-035)  position-independent always-checks, run by `validate` + surfaced on status
    - id:    <slug>                # core      stable identifier
      check: <predicate>           # core      the predicate (same shape as detection/gates); True = holds; indeterminate is fail-closed
      why:   <prose>               # core      explanatory prose surfaced on a violation
      applies_to: <state?>         # core (optional, COR-040)  scope to one state; ABSENT = process-wide
  interface:                       # core (optional, COR-036)  composition: { inputs, outcomes } — the public embedding contract
    version:  <int>                              # core (optional, COR-053)  the INTERFACE version — changes only when this contract breaks
    inputs:   [{ name, meaning?, required? }]   # core      what the inner needs to start
    outcomes: [{ name, meaning? }]              # core      named terminal states a parent may wire
  orchestration: { overflow, cross_gates }   # deferred  altitude-2 (overflow / hand-off — concurrent spawn)
```

What a definition must hold, and how its parts are written:

- **Required:**
  - a process's `id`, `version`, `subject`, `states` and `transitions`, and a subject's `cardinality`
  - a state's `id`, `meaning` and `detection`, and a detection's `mode` and `predicate`
  - a transition's `from`, `to`, `trigger` and `authorisation`, and a gate's `kind`
- **Every other field is optional,** but a block that is declared carries required fields of its own (below).
- **A transition with no `gate`** has no check, and the engine lets any caller take it.
- **A predicate** is `{run: <command>, with: {...}}`. `run` names a command the owning capability registers, and `with`, optional, maps static arguments, which the runner does not pass yet.
- **An entry** is `true`, an unconditional start, or `{when: <predicate>}`, a start guarded by a predicate.

A block that is declared requires these fields:

- **A predicate:** `run`.
- **A gate:** `predicate` for `deterministic` and `authorisation-artifact`, and `outcome` for `subprocess-outcome`. A `cascade-outcome` gate takes neither.
- **`blocked`:** `blocked_on`, and `resume_when` for `awaiting-condition`.
- **`subprocess`:** `runs`, and `subject` where the inner process is keyed.
- **`cascade`:** `runs`, `members`, `membership` and `reducer`. The reducer takes `op` and `outcome`, and `threshold` under `count`.
- **An invariant:** `id`, `check` and `why`.
- **A `depends_on` entry:** `upstream`, `relation`, `mode` and `why`. A `mandatory` mark takes `reason`, and a `handoff` takes `trigger`, `candidates` and `resolve`.
- **An `interface`'s inputs and outcomes:** each a `name`.

The connections page describes how the engine reads `subprocess`, `interface`, `cascade` and `depends_on`. The process README's predicate runner says how each predicate is run and read.

## Subject cardinality (core)

A process declares `subject.cardinality`, which is `singleton` or `keyed`.

- **`singleton`:** one journey for each process. It has no subject identifier, and the engine tracks the one journey under a fixed internal key, `_`. Its predicates receive `_` as their subject.
- **`keyed`** ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)): many units under one definition, each at its own position, such as one for each issue. The engine works on one subject identifier it is given:
  - It resolves that subject's position, validates and executes that subject's moves, and writes that subject's journal.
  - It passes the identifier to every predicate it runs, as the predicate's first argument.
  - The identifier is required, with no singleton default. Each of the engine's operations on one of its subjects must be given `--subject <id>`, and fails with a clear error without it.
  - A keyed subject may declare a descriptive `key`, naming what identifies a unit, such as `issue-number`. The engine does not interpret it.
  - A subject identifier must be safe to use in the path of that subject's journal. The singleton's `_` is refused as a keyed subject's identifier.

**The engine never enumerates** a keyed process's subjects. It only ever acts on the one it is given.

- **The one exception** is the cascade fold ([COR-037](../decisions/core/COR-037-process-cascade.md)), bounded tightly. A parent reads across the members of one declared child process, scoped to one parent subject. It does so only through a membership predicate that the capability supplies, run on one subject at a time.
- **Never a tree or a listing.** The engine holds no tree of what contains what, and offers no general way to list subjects.
- **Everywhere else** the rule against enumerating holds unchanged. project-management's forward cascade, which moves a parent's position, stays inside that capability until a binding needs the shared form.

**What each subject has at run time:**

- **A position** (core), resolved live.
- **A derived blocked state** (core): "no legal move", with an optional declared wait, `blocked` ("Blocked" below).
- **A journal** (optional audit): an append-only record of how the subject got here. It is kept only where the project turns journal logging on, which is off by default. Nothing the engine decides reads it, and the process README's "An entry" describes its entries.

## Detection modes (core)

Each state's `detection` declares the mode in which reality is asked ([COR-033](../decisions/core/COR-033-process-substrate.md) point 5). Both modes read reality live on every invocation, and keep nothing between invocations. They differ in the question the predicate is asked:

- **`inferred`:** "is the subject in this state?" Each state names its own predicate, which answers `{result, reason}`.
- **`classified`:** "which state is the subject in?" A predicate that states name is a *classifier*. It answers `{state, reason}`, and the states that name it, *its states*, share its one answer.
  - Two detections name the same classifier when they name the same command with the same `with` mapping.
  - A definition may have several classifiers, and a classifier may have a single state. A check on one state alone is a classifier that answers that state or `null`.
- **`detail`** is optional under both modes. The declared mode selects how an answer is read, and the shape of an answer never does.
- **Deferred:** `stored` and `hybrid`, modes that keep a position between checks.

### One mode per definition

Every state of a definition declares the same mode.

- **Per definition.** An embedded inner process, or the child process a cascade folds, is a definition of its own, and is read by its own mode.
- **A definition that mixes modes** does not conform. Validation's `process` member reports it as an error, and the engine runs none of its detections.
- **Its states.** Every state of such a definition is indeterminate, for one reason that names each mode and the states that declare it. So no position is ever resolved from some of the states.

### How a classifier's answer is read

The engine runs a classifier once each time it resolves a subject's position, once for all of its states, never once for each state. It reads the one answer for each state S of the classifier:

- **`state` is S's id:** S's detection is true.
- **`state` is the id of another of the classifier's states:** S's detection is false.
- **`state` is `null`, and `reason` is a string that is not blank:** a reason that holds something other than whitespace. Every one of the classifier's states is false, so it places the subject in none of them.
  - This is the only way to say so.
  - The reason is what `status` shows beside "no position". It is all that tells a deliberate "none" from an accident, so a blank one is no reason.
- **Any other answer is unreadable,** and every one of the classifier's states is indeterminate. An unreadable answer is one of these:
  - an answer with no `state` key
  - `null` without a reason, or with a blank one
  - a value that is neither a string nor `null`
  - the empty string
  - a string that names no state of the classifier's: a state the definition does not declare, or one that names another classifier
- **Ids** are compared exactly, with no trimming and no case folding.
- **No answer at all** leaves every one of the classifier's states indeterminate too, as it leaves any predicate. No answer is a non-zero exit, a timeout, or output that is not one JSON object.
- **A `result` beside `state`** is not read, since the mode has already chosen the reading.

A subject's position may be resolved more than once in one invocation, as a cascade member's is. So a classifier may run more than once, and it answers from reality each time.

### How an `inferred` definition is read

Each detection is read by its `result`. A `state` beside it is not read, and an answer with no `result` is false, not indeterminate. The process README's predicate runner says how a `result` is read.

- **Where the two modes differ:** a missing `state` under `classified` is indeterminate, and a missing `result` under `inferred` is false.
- **One limit follows.** A classifier's command named in an `inferred` definition reads as false for each state that names it. Where every state names it, every subject resolves to a determinate "no position". The engine cannot tell, because it reads an answer by the declared mode.

### Where the reading applies

The mode's reading applies in one place: where the engine resolves position from a state's `detection`. Everything else that needs a position takes it from that resolution.

A predicate declared anywhere else carries no `mode`, and is read by its own kind's reading, whatever its answer contains. Such predicates include:

- a gate, and an entry guard
- an invariant's `check`, and a `resume_when`
- a cascade's `members` and `membership`
- the seams of a hand-off contract

### Position: the precedence rule

The position is the first state, in declaration order, whose detection is true. Each state's detection comes out true, false or indeterminate. Failing that, it is indeterminate if any detection was, and failing that, it is none.

- **One classifier** makes at most one of its states true. So in a definition with a single classifier, the order of states decides nothing.
- **Several classifiers** resolve as several `inferred` detections do. Where two each place the subject, the state declared earlier is the position.
- **A classifier that fails,** or whose answer is unreadable, makes the position indeterminate only when no other classifier's state is true.
- **Under `inferred`,** the same rule makes declaration order load-bearing wherever two detections can both be true.

### A mode the engine does not implement

Handed a definition in a mode it does not implement, an engine treats every state's detection as indeterminate, and says the mode is not implemented.

- **The position is then indeterminate:**
  - `move` refuses.
  - `health` lists the subject as indeterminate.
  - A cascade holds its fold.
- **Every engine shipped before `classified`** does this with a `classified` definition.
- **A capability whose definition uses the mode** declares the backbone it needs (`requires_backbone`). That floor guards install, upgrade and validation. This reading is all that guards a running binary older than the floor.
- **An engine older than the one-mode rule** cannot enforce it. It would evaluate a mixed definition's `inferred` states alone, and could place the subject by them. So a mixed definition has no reading to rely on under any engine.

### What validation reports

Validation's `process` member reports three faults in every definition the installed capabilities declare, each as an error:

1. Its states declare more than one mode.
2. Its `classified` detections name one command under different `with` mappings.
3. Two or more states of an `inferred` definition name one predicate.

What each fault means:

- **Different mappings of one command** are separate classifiers, each with only its own states. The runner gives both the same input, so an answer that one of them can read is unreadable for the other. What `with` means to the command is not decided yet, and the runner does not pass it.
- **Two detections name one predicate** when the engine's answer memo gives them one key: the same command under the same `with` mapping. A detection that names no command has no key.
- **Such a predicate runs once,** and each of its states reads the same answer. So none of them but the one declared first can be the position. The usual way there is the limit above, a classifier's command named under `inferred`.

What is not reported, and why the member is needed:

- **One command under different `with` mappings** is several predicates to the answer memo, and is not reported under `inferred`.
- **A definition that mixes modes** is reported for the mix alone.
- **The shape contract's schema** states the one-mode rule too, so the authoring stamps' lint and an editor see it.
- **A capability's companion schema** may restate the process block, as project-management's does, and the shape contract does not reach it. That is why the `process` member is the check that covers every definition.

### What it shows

The states of a classifier that gives no answer carry the one cause, and the one tail of what the predicate wrote on standard error.

- **An unreadable answer** is shown the same way. Its reason names the predicate and quotes what it answered, bounded and with control characters removed, as a standard-error tail is.
- **`status --json`** keeps one `position.unevaluated` entry for each state.
- **The narrative views and a refusal** print the cause, and what the predicate said, once for each classifier. The states it leaves indeterminate are listed beside it. A definition that mixes modes is shown the same way.
- **When no state is true,** the narrative `status` shows, under "no position", the reason of each classifier that answered `null`.
- **`status --json`** carries the same as `position.placed_nowhere`: one `{predicate, reason}` entry for each such classifier, with `predicate` naming its command. It is empty when a state is true, and always under `inferred`.

## Blocked — a first-class wait (core)

A subject may declare a wait, `blocked`, on its `subject` block ([COR-034](../decisions/core/COR-034-human-pause-gate.md)). The engine derives live whether the subject is blocked now, and clears the wait as its reason says. The block is optional.

```
subject:
  blocked:
    blocked_on: awaiting-human | awaiting-condition | awaiting-subprocess-outcome | awaiting-cascade-outcome   # WHY it waits (open to additive widening)
    resume_when: <predicate>                          # awaiting-condition ONLY (required); forbidden for the other three; re-evaluated LIVE, auto-clears
    assignee:    <owner?>                             # optional: who owns the wait (audit colour)

transitions:
  - from: ...
    authorisation: user
    prompt: <question>                                # optional: the QUESTION posed to the person (awaiting-human)
```

### The four reasons

`blocked_on` takes one of four reasons. A definition declares one wait, on its subject block.

- **Three are read from one subject's reality** ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)):
  - **`awaiting-human`:** a person must act.
  - **`awaiting-condition`:** an external fact must become true.
  - **`awaiting-subprocess-outcome`** ([COR-036](../decisions/core/COR-036-process-composition.md), one inner process): the subject is parked in a `subprocess` state. Its embedded inner process has not yet reached a wired terminal outcome. The connections page describes composition.
- **The fourth, `awaiting-cascade-outcome`** ([COR-037](../decisions/core/COR-037-process-cascade.md)), is the one sanctioned wait across subjects. The subject is parked at a state whose outgoing `cascade-outcome` gate folds across one declared child process's members. The fold has not yet resolved open. The connections page describes the cascade.
- **The set is open to additive widening.** The remaining reason across subjects, `deadlock`, a cycle of peer subjects, joins it where the engine reads across a crowd of waiting subjects. It is deferred.
- **The cascade's wait cannot deadlock.** The fold is acyclic by construction, since it waits only on members' terminal outcomes, already resolved.

### How each wait clears

The blocked flag is a derived overlay, recomputed live and never stored as truth. Each reason resumes in its own way ([COR-034](../decisions/core/COR-034-human-pause-gate.md)).

- **`awaiting-human`** carries no `resume_when`, which the schema forbids.
  - **Blocked:** while the subject sits at a non-terminal position with an outgoing `user` move not taken yet. The move's gate may be open, ready to take, or closed, so that the person must change reality first.
  - **Unless the engine can move on its own:** an `agent-autonomous` or `script` move that is allowed now, its gate open or absent, is a way forward without a person. The subject is not waiting then. A gate-closed autonomous move lifts no wait.
  - **Resumes:** when the person takes the move. The position advances off the parked state, which removes the pending move.
  - **No side-predicate:** a side-fact, such as a review file that exists, must not clear an "approve?" wait. Only taking the move does. A side-fact can hold while the move's gate is still closed, and would report "not waiting" on a stuck subject.
- **`awaiting-condition`** carries a required `resume_when` predicate.
  - **Blocked:** when the subject has no legal move, and its `resume_when` does not hold yet. No legal move means a non-terminal, determinate position out of which no transition is allowed.
  - **Resumes:** when `resume_when` holds. The engine clears the flag on its own, with no person involved.
  - **Fail-closed:** an indeterminate `resume_when` keeps the subject blocked, rather than resume it silently.
- **`awaiting-subprocess-outcome`** carries no `resume_when`, which the schema forbids.
  - **Blocked:** while the subject sits in a `subprocess` state with no legal move. No `subprocess-outcome` gate passes then, since the embedded inner process has not reached a wired terminal outcome.
  - **Resumes on its own,** as `awaiting-condition` does. Its condition is the inner process's resolution, which the `subprocess-outcome` gates carry, re-read live in the check for a legal move. When a wired inner outcome resolves, a gate opens. A legal move then exists, and the wait clears.
  - **An unwired outcome:** a parent parked on an inner outcome that no transition wires stays blocked, correctly. The author owns the wiring of outcomes to transitions, not the engine.
- **`awaiting-cascade-outcome`** carries no `resume_when`, which the schema forbids.
  - **Blocked:** while the subject sits at a state whose outgoing `cascade-outcome` gate has no legal move. The fold over the declared child's members has not resolved open then.
  - **Resumes on its own,** its condition being the live fold, re-read in the check for a legal move. When all members reached the outcome, or the threshold is met, the gate opens. A legal move then exists, and the wait clears.
  - **Fail-closed throughout:** any unresolved member holds the fold shut, and so does an empty member set, unless the cascade's `on_empty` is `satisfied`. The parent stays blocked.

### The journal of a wait

Where the project keeps a journal, the engine journals a wait as it starts and as it ends ([COR-034](../decisions/core/COR-034-human-pause-gate.md)). The journal is the audit trail, and whether the subject is blocked now is always the live reading, which wins over any journal entry. The process README's "Journaling a wait" says when each entry is written.

### The question on a person's move

An `awaiting-human` wait carries a `prompt`, the question, written on the `user` move.

- **Where it shows:** with that move, and on the wait, for the view of a person's pause. The park becomes "your move: here's the question", not a silent "your move".
- **Content-free:** the engine carries and shows `prompt` and `blocked_on`, and never interprets them.

### A wait is not a state

A wait annotates the subject at its current position. It adds no state to the process, so it cannot multiply the states.

- Position is still read live from reality.
- The validator stays deterministic, since `resume_when` is a predicate over reality, as a detection is.

### Deferred waits

Each of these waits for a decision of its own, once a binding needs it ([COR-034](../decisions/core/COR-034-human-pause-gate.md)):

- **`deadlock`,** the remaining reason across subjects: a cycle of peer subjects. It differs from composition's guard against cycles ([COR-036](../decisions/core/COR-036-process-composition.md)), and from the cascade's wait, acyclic by construction ([COR-037](../decisions/core/COR-037-process-cascade.md)).
- **The `hooks` mechanism:** notify on enter, act on resume.
- **A structured `selection`,** a set of options for the person. Until it ships, write the options in the prompt's text.

## Invariants — position-independent always-checks (core)

An invariant answers a third question, beside detection and gates: is something that must always be true, true ([COR-035](../decisions/core/COR-035-process-invariants.md))? Detection answers "where is this subject?", and a gate answers "may it move from here to there?". A process may declare a list of invariants on its `process` block, each holding process-wide, across every state.

```
process:
  invariants:
    - id:    <slug>          # stable identifier (reported by validate + on status)
      check: <predicate>     # the predicate — SAME shape detection/gates use; True = holds
      why:   <prose>         # explanatory prose surfaced when the check fails
      applies_to: <state?>   # core (optional, COR-040)  scope to one state; ABSENT = process-wide
```

- **Process-wide by default.** An invariant is checked wherever the subject is: it is a property of being anywhere in the process, not of moving. The engine evaluates it against current reality whatever the resolved position. An indeterminate or absent position does not stop it being checked.
- **Scoped to one state, optionally** ([COR-040](../decisions/core/COR-040-process-open-region.md)). `applies_to: <state>` scopes an invariant to one state, the open region ("Determinism across dynamic structure" below). The engine then filters the report on the resolved position:
  - An unscoped invariant stays process-wide.
  - A scoped invariant is evaluated and shown only when the resolved position is its state.
  - It is not applicable, neither evaluated nor shown, while the subject is in another state, or its position is indeterminate. The engine cannot confirm the region then, so it never reports a violation outside it.
  - The filter couples no invariant to a move. A region's boundary is held by its exit gate, not by the invariant, so invariants still only report.
- **Read-only, content-free, one subject.** The engine runs each `check` through the same predicate runner as detection and gates, threaded with the subject's id. It reports the result, with the `why` on failure. It never interprets what an invariant means, and never reads across subjects ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)).
- **Fail-closed.** An indeterminate `check`, one that errors, times out, answers unparseable output or does not resolve, is reported as not holding. A check that cannot be confirmed counts as a violation, as an indeterminate `resume_when` keeps a wait.
- **Shown on every status read, and enforced by report only:**
  - A violation is shown on the status view. An agent reading status sees it on every read, and a binding's wrapper declines what follows.
  - The engine's `validate` operation reports it too, narrative or `--json`, and exits non-zero on any violation.
  - A violation does not block moves, fail transitions or remediate. A binding that wants a hard gate everywhere writes it as a gate predicate.
  - The status narrative shows only violations, to stay short. `status --json` and `validate` carry the full set.
- **Determinism kept.** An invariant is a predicate over reality, like a detection predicate, so the engine stays a deterministic validator.
- **The open region's boundary.** A region-scoped invariant shows on status as the reason the region's exit gate is shut. The boundary is enforced by composing the gate, not by blocking moves: the exit gate's predicate checks the region's conditions. So invariants report, and the exit gate checks.
- **Deferred,** each for a decision of its own when a binding needs it ([COR-035](../decisions/core/COR-035-process-invariants.md)):
  - an invariant's severity, and remediation
  - always-checks across subjects, which need the breadth that COR-032 holds back

## Determinism across dynamic structure

Whatever form a transition's target or gate takes, the engine stays a deterministic validator. A process need not be a fixed pipeline: the target or gate takes one of three forms ([COR-033](../decisions/core/COR-033-process-substrate.md) point 6):

- **Static** (core): listed in the definition.
- **Resolved** (deferred): a `resolver(data)` that returns which of a known set of blocks apply now. Given the data, its answer is deterministic, so the engine stays an honest validator.
- **An open region** (core, [COR-040](../decisions/core/COR-040-process-open-region.md)): a state marked `open_region: true`, with no edges inside it, for work whose order is open-ended. Only region-scoped invariants and an explicit exit gate bound it, and the flag itself changes nothing the engine does.

### The open region

An open region adds no new kind of node, and no language for states inside it ([COR-040](../decisions/core/COR-040-process-open-region.md)). The engine reduces it to a deterministic check on its boundary: "may this subject leave yet?"

- **Staged work inside it** is a composed process ([COR-036](../decisions/core/COR-036-process-composition.md)), whose outcome the exit gate reads. It is never an edge inside the region.
- **Built from existing parts:**
  - Region scoping is a filter on the invariant report, keyed on the resolved position.
  - Enforcement is the exit gate, an ordinary `deterministic` or `authorisation-artifact` gate whose predicate checks the region's conditions. It is not an invariant that blocks moves, so invariants still only report.
- **A shut exit is a closed gate,** a determinate "not yet". Status names the region-scoped invariants not met as the reason it is shut.
- **A compound exit is not one gate.** An instance is "(readiness predicate) AND (sign-off by another authority)":
  - The sign-off stays an `authorisation-artifact` gate that the engine computes. Folded into a `deterministic` predicate, it would lose the check on who signed.
  - Any hard structural AND lives in the binding's wrapper.
