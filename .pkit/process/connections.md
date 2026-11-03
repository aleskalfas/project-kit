---
reader: act-ai-agent
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
        - src/project_kit/package_validate.py
        - src/project_kit/capabilities.py
        - .pkit/schemas/_defs/process.schema.json
      record: [COR-006, COR-030, COR-032, COR-033, COR-034, COR-035, COR-036, COR-037, COR-038, COR-042, COR-044, COR-053, "ADR-023#1", ADR-048, ADR-062]
      artefact:
        - .pkit/process/shape.md#the-fields
        - .pkit/process/shape.md#blocked--a-first-class-wait-core
        - .pkit/lifecycle/README.md#the-connection-documentation-and-friction-blocks
---

# Connections between processes

How one process reads another's outcome, folds the outcomes of many, or declares a connection the engine never reads ([COR-033](../decisions/core/COR-033-process-substrate.md)). Composition and the cascade are the engine's to resolve, and `depends_on` is metadata that the engine's runtime never reads. Their fields are listed with the rest of a definition's in [the shape page's "The fields"](shape.md#the-fields).

## Contents

<!-- pkit:contents -->
- [Composition — cross-process outcome resolution (core)](#composition--cross-process-outcome-resolution-core)
- [Cascade — fold one child process's member outcomes (core)](#cascade--fold-one-child-processs-member-outcomes-core)
- [depends_on — inert cross-process connection metadata (core, COR-038)](#depends_on--inert-cross-process-connection-metadata-core-cor-038)
<!-- /pkit:contents -->

## Composition — cross-process outcome resolution (core)

A process may resolve another process's terminal outcome, and read it as an input to a gate of its own ([COR-036](../decisions/core/COR-036-process-composition.md)). It is the engine's one capability across processes.

- **The interface.** A process exposes a public `interface`: `inputs`, what it needs to start, and `outcomes`, its named terminal states. A `terminal: true` state is an outcome.
- **Embedding.** A parent embeds one inner process through a `subprocess` state that `runs: <capability>:<process-id>`. It supplies the inner process's inputs on entry, and wires the inner process's outcomes to its own outgoing transitions.
- **All coupling lives in the parent.** The child references nothing upward, so it is reusable and knows no parent.
- **The timing it ships:** nest and call, where a parent waits for an inner process's outcome. The cascade builds on this resolution, as its step for each subject ("Cascade" below).
- **The timing still deferred:** overflow and hand-off, where a terminal state spawns or unblocks a concurrent sibling process. That is the orchestration altitude.

The definition declares it so. The block is optional:

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
      trigger: <command>
      authorisation: agent-autonomous
      gate:
        kind: subprocess-outcome             # the ENGINE computes this — no capability predicate
        outcome: <inner-terminal-state>      # the move opens iff the inner reached exactly this outcome
```

### How the engine resolves an inner outcome

The engine resolves the outcome of one inner process whose subject is determinate, and never enumerates.

- **A determinate subject.** The inner process is a `singleton`, with no id, or `subprocess.subject` supplies the one id of a keyed inner process. A keyed inner process with no subject supplied fails closed, by the rule that a keyed subject is required ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)).
- **One subject, never many.** The engine resolves that one subject, and never enumerates a keyed inner process's subjects. Folding across many is the cascade's, which calls this resolution once for each subject it folds.
- **A new engine for the inner process.** While the subject is parked in a `subprocess` state, the engine builds a new engine on the inner address and the determinate inner subject. It reads the inner process's terminal state through that engine's own resolution of position.
- **The engine computes the gate.** The engine computes a `subprocess-outcome` gate on the parent from the inner process's outcome, and the gate takes no predicate. It passes when the inner process reached exactly the gate's named `outcome`.
- **Read-only.** Running `status` resolves the inner process, and writes neither journal.

### No cycles

A process may not embed itself at the same subject, directly or through others.

- **The guard.** The engine tracks the stack of active resolutions, each an address with a subject. It refuses an address and subject already on the stack.
- **The same process at other subjects** is no cycle. A cascade over other subjects of the parent's own process is allowed, such as a container that closes once its children have.
- **One level deep.** A resolution reads the inner process's detected position, and never recurses through the inner process's own `subprocess` or `cascade` gates. So in practice the guard refuses only a direct self-embedding: A at subject S running A at S.
- **Fail-closed.** The refusal is shown as an unknown gate kind is: indeterminate, with `cyclic embedding refused` and the chain in its reason. A cyclic resolution never ends, so it has no definite answer.
- **Not a deadlock.** This guard differs from the deferred `deadlock` reason ([COR-034](../decisions/core/COR-034-human-pause-gate.md)), a cycle of peer subjects in another graph.

### Waiting on the inner process

While the inner process has not reached a wired terminal outcome, the parent has no outgoing move it can take.

- **The wait.** The parent is parked under the `awaiting-subprocess-outcome` reason ([the shape page, "Blocked"](shape.md#blocked--a-first-class-wait-core)). The wait clears itself, and its condition is the live resolution.
- **An unwired outcome.** A parent parked on an inner outcome that no transition wires is correctly still waiting, not a case to handle apart. The author owns the wiring of outcomes to transitions.
- **Determinism kept.** A subprocess state's position is the inner process's terminal outcome. The inner definition's own detection reads that outcome from reality, in its own mode.
  - So "where is the subject?" becomes "what outcome did the inner process reach?", a composed, definite answer.
  - Resolution is one level deep, so the composition ends. Position is still read live from reality, and the validator stays deterministic.

### The interface version

An interface may carry an integer `version`: the version of the public contract ([COR-053](../decisions/core/COR-053-connection-points.md) point 5).

- **When it changes:** only when a change breaks the processes that connect to it. An additive change leaves it alone.
- **Not the definition's version.** The definition's own `version` tracks internal change under live subjects.
- **Who reads it:** validation alone. The engine resolves outcomes live, as it does without one.
- **Offered under a role.** A capability that offers the process under a role declares the same integer as the offered point's `schema_version`, in its package metadata. Validation reports an offered point whose `schema_version` differs from the definition's `interface.version`, naming both values and both files.
- **Targeted from `depends_on`.** A `depends_on` entry targets it with a `version` of its own ("depends_on" below).

### What `status` shows

`status` shows the embedded inner process, and its outcome resolved live.

- **The narrative:** an `embeds <address>` line, and an `inner outcome: <x>` line.
- **`--json`:** a `position.subprocess` object, `{runs, outcome, indeterminate, reason, stderr_tail}`.

**Deferred,** each for a decision of its own when a binding needs it ([COR-036](../decisions/core/COR-036-process-composition.md)):

- the overflow and hand-off timing, a concurrent spawn
- the broader orchestration altitude

## Cascade — fold one child process's member outcomes (core)

A parent process may look across all the members of one named child process that belong to it, and ask one question ([COR-037](../decisions/core/COR-037-process-cascade.md)). The question is "did every one reach outcome X?", or "did at least N?", and its answer may open a parent gate.

- **The one bounded exception.** It is the one sanctioned place where the engine reads across many subjects, crossing the rule against enumerating as little as it can ([COR-032](../decisions/core/COR-032-keyed-process-subjects.md)):
  - only through one declared child relation, scoped to one parent subject
  - only through a predicate the capability supplies, run on one subject at a time
  - never a general reopening of enumeration
- **From child to parent, with the coupling in the parent,** as composition has it. The parent declares the fold over one named child. The child references nothing upward, and stays reusable.
- **Composition's resolution is its step.** The fold resolves each member through composition's resolution of one inner subject ([COR-036](../decisions/core/COR-036-process-composition.md)), and invents no rival path across processes. So the cascade adds breadth across a finite member set, never depth. It does not recurse into the members' own `subprocess` or `cascade` gates.

The definition declares it so. The block is optional:

```
process:
  cascade:                               # the parent's child → parent fold declaration
    runs:    <capability>:<process-id>   # the one named child process whose members are folded
    members:    <predicate>              # parent-scoped candidate-member SOURCE — returns { members: ["id", ...] }
    membership: <predicate>              # per-candidate re-confirm, given the candidate alone: it can be read, and is still a member
    reducer:
      op:        all | count             # all = every member reached `outcome`  |  count = at least `threshold` did
      outcome:   <child-terminal-state>  # the child OUTCOME each member is folded against
      threshold: <int>                   # required for `count`, forbidden for `all`
    on_empty:  fail-closed | satisfied   # optional: a DETERMINATELY empty member set keeps the gate shut (default) or opens it
  states:
    - id: <waiting-state>
      meaning: <prose>
      detection: { mode: inferred, predicate: <ref> }
  subject:
    blocked: { blocked_on: awaiting-cascade-outcome }   # the aggregate wait while the fold has not opened
  transitions:
    - from: <waiting-state>
      to:   <closed>
      trigger: <command>
      authorisation: agent-autonomous
      gate:
        kind: cascade-outcome            # the ENGINE folds the `cascade` declaration — no predicate, no per-gate outcome
```

### The binding supplies the set, and the engine folds

The engine holds no tree of what contains what, and discovers none.

- **The candidates.** The engine obtains the parent's candidate member ids from the `members` predicate.
  - It runs once, threaded with this parent subject, and returns `{members: [...]}`.
  - It is read live, and is determinate at the instant, never a stored or open-ended global listing.
- **Each candidate confirmed.** The engine confirms each candidate with the `membership` predicate. It runs on one subject at a time, through the runner for one subject, threaded with the candidate alone.
- **Scoping is the `members` predicate's.** The `membership` predicate never receives the parent, so it cannot re-scope to it. It confirms that the candidate can be read and is still a member of the relation.
- **The seam for the candidate set.** The `members` predicate is content-free, and the binding supplies it, as detection gets its inputs. The engine never receives or holds a global list of subjects.

### The two fold operations

One machine folds the members, with two reducers:

- **`all`:** every member reached the reducer's named `outcome`.
- **`count`:** at least `threshold` members reached it, a saturation floor.
- **Richer reducers,** such as ratios, weights or custom ones, stay deferred until a binding needs one.

### Fail-closed

The fold opens only on members it could resolve, and holds shut on any doubt.

- **An unresolved member.** A member whose outcome is unresolved or indeterminate holds the whole fold unresolved, such as one still moving, parked or indeterminate. The gate stays shut, never a false "all reached X".
- **An indeterminate membership test** holds the whole fold unresolved too, as an unresolved member's outcome does. The `membership` predicate errored or timed out for a candidate.
  - Dropping the candidate silently would look like fewer members, and could let an `all` pass vacuously.
  - A determinate `result: false` cleanly excludes a real non-member.
- **A determinately empty set** is decided by the cascade's `on_empty`, and the reducer is not evaluated ([COR-037](../decisions/core/COR-037-process-cascade.md)):
  - `fail-closed`, the default, keeps the gate shut: a determinate "not yet", never true.
  - `satisfied` opens it, for a parent with nothing to wait on.
  - The set covers a parent with no candidates, and a parent whose candidates are none of them members. The two collapse on purpose.
- **Doubt overrides `on_empty`.** Where enumerating the candidates or testing a membership errors, the fold stays unresolved, even under `satisfied`.

### The aggregate wait

A parent gated by a cascade parks under `awaiting-cascade-outcome`, a wait that clears itself, in the model of [the shape page's "Blocked"](shape.md#blocked--a-first-class-wait-core).

- **No `resume_when`:** the live fold is its condition. It clears the instant the fold resolves open and a legal move exists.
- **Acyclic by construction.** The parent waits only on its members' terminal outcomes, already resolved, and a terminal subject waits on nothing. So the wait cannot join a wait cycle, and the deferred `deadlock` reason is safe here by construction, not by hope.

### Read-only, deterministic, one level

Resolving the fold runs predicates and resolves member outcomes live, and writes nothing.

- **Deterministic:** the fold is a deterministic reduction over a finite member set. Each member's outcome is a composed, definite answer, and the membership set is a live reading of a deterministic predicate.
- **No cycles:** the guard against cycles is inherited. A member at the parent's own address and subject is refused, and a member at another subject of the parent's own process is allowed.
- **A known limit, accepted:** predicate answers are not memoised across the breadth of a fold.
  - The `members` predicate runs through the parent's answer memo for the invocation.
  - Each member's outcome and membership are resolved through a fresh runner, whose memo starts empty. One `status` resolves the fold more than once, so a member's predicates run again each time.
  - The member sets that bindings fold are small. A shared memo for each render is deferred until a binding's set size makes it pay.

### What `status` shows

`status` shows the live fold when the current state has the move that a cascade gates.

- **The narrative:** a `folds <address> (<op>)` line, and a `fold: <reached>/<total> …` line.
- **`--json`:** a `position.cascade` object, `{runs, op, outcome, threshold, reached, total, opened, indeterminate, reason, stderr_tail}`.

**Deferred,** each for a decision of its own when a binding needs it ([COR-037](../decisions/core/COR-037-process-cascade.md)):

- **The forward cascade,** which moves a parent up to match its furthest child. It reduces positions, and folds no terminal outcomes. project-management keeps it in its own capability.
- **Richer reducers:** ratios, weights or custom ones.
- **Overflow and hand-off:** a terminal state that spawns or unblocks a concurrent sibling, the orchestration altitude.
- **A deadlock among peers, and invariants across subjects:** each is a different machine across subjects, with a slot of its own.

## depends_on — inert cross-process connection metadata (core, COR-038)

A state's `depends_on` list declares the state's connections to other processes ([COR-038](../decisions/core/COR-038-process-connections.md)). The engine never acts on it, and it adds no engine capability.

- **What it is:** declared metadata, checked for its shape so that it is uniform and machine-readable.
- **Who draws it:** the render reads it to draw the project's whole configured wiring.

The definition declares it so. The block is optional:

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

### Who reads it

The engine's runtime never reads `depends_on`, and each other reader is bounded to one purpose ([COR-042](../decisions/core/COR-042-process-health.md), then [COR-053](../decisions/core/COR-053-connection-points.md) point 6).

- **Never the runtime.** The engine's runtime operations, `status`, `can-move`, `move` and `validate` of a position, never read it, and no gate does.
- **Its readers:**
  - **the schema,** which checks its shape: a well-formed `upstream` address, `relation` and `mode` from their closed sets, and a `why`. A `mandatory` mark comes only with a reason.
  - **the render,** outside the engine, which reads the declarations alone
  - **the health check,** outside the runtime and report-only, which reads the entries that carry the optional `handoff` contract, and nothing else
  - **the capability lifecycle,** install, upgrade and uninstall, which reads the `mandatory` mark alone. It reads the mark from the package's generated copy ("The generated `depends-on` list" below). It reads it only to check that the upstream definition exists, at a compatible interface version where the entry names one.
- **Entries with neither a contract nor a mark** are evaluated by nothing. That is one level more inert than invariants ([COR-035](../decisions/core/COR-035-process-invariants.md)).
- **A malformed entry** stays a lint error at authoring time, in schema validation, never a gate that fails closed. It cannot affect whether any subject may move.
- **A contract that cannot be interpreted** at health time is reported indeterminate, never silently green ([COR-042](../decisions/core/COR-042-process-health.md)). An instance is an upstream address that does not resolve, or a trigger state the upstream does not declare.

### Addressing an upstream by role

`upstream` takes one of two forms ([COR-053](../decisions/core/COR-053-connection-points.md) point 2).

- **The implementation form,** `<capability>:<process-id>`, names one capability's definition.
- **The role form,** `<publisher>::<role>:<point>`, names a process offered under a role. It reaches whichever installed capability is that role's active provider.
  - A capability declares the role among its `connections.roles`, and the process under `extension-points.offers` ([the lifecycle README, "The connection, documentation and friction blocks"](../lifecycle/README.md#the-connection-documentation-and-friction-blocks)). Both sit in its package metadata.
  - Replacing that capability with another that provides the same role touches nothing in this definition.
- **Scoped to `depends_on`.** Embedding, by `subprocess` and `cascade`, stays addressed by implementation, since a role there would make the engine consult the wiring.
- **Both forms are valid.** Definitions that use the implementation form keep working unchanged.
- **A targeted version.** An entry may name the upstream interface `version` it targets ("The interface version" above). It then connects only to an offered process at an equal version, and another version leaves it inert.
- **A hand-off contract on an entry addressed by role:**
  - The health check reads the process that the role's active provider offers there, from the wiring resolver, never by a resolution of its own.
  - An address no active provider offers is indeterminate, in three cases:
    - no provider is installed
    - providers conflict
    - no process sits at that address
  - The hand-off stamp reads the same process when it writes the contract, and checks the trigger against its states. A role address that reaches no offered process is a warning there, since the trigger cannot be checked.
  - The `candidates` seam still receives the address as declared.

### The mandatory mark

A connection is optional unless its entry says, with a reason, that it is mandatory: `mandatory: { reason: <prose> }` ([COR-053](../decisions/core/COR-053-connection-points.md) point 6). The mark without a reason is refused.

- **What it means:** the upstream process definition must exist, at a compatible interface version when the entry names one.
- **Who reads it:** the capability lifecycle, and nothing else. It splits by direction, as capability dependencies do ([COR-030](../decisions/core/COR-030-capability-dependencies.md)):
  - Installing, registering or upgrading the capability that carries the mark is refused while the upstream is missing or incompatible. The refusal quotes the reason.
  - Upgrading or uninstalling the capability it targets is warned about, each counterpart named, and proceeds only under `--force`. It is never a hard block, so it cannot deadlock.
- **Validation** reports an unmet mark as an error on the carrier's package. It reports two marks facing each other as a cycle that no install order could satisfy.
- **The wording** of the refusal and of the warning is the CLI reference's.

### The generated `depends-on` list

The capability's package metadata carries the same connections as one list, `connections.extensions.depends-on` ([COR-053](../decisions/core/COR-053-connection-points.md) point 4).

- **Why a copy:** a reader, and a plan for a capability not yet installed, sees the connections without opening a definition. The lifecycle reads the marks without parsing definitions.
- **Its single source** is the definitions. The refresh regenerates the list, and marks it `generated: true`:
  - one entry for each distinct upstream and targeted version, sorted
  - each entry carrying `process` and `schema_version`, the entry's `version`
  - an entry carrying the `mandatory` mark too where any declaring entry carries one
- **Never write it by hand.** Validation fails a copy that differs from what the definitions generate, and names the refresh as the fix. The definition always wins.
- **Where and when to refresh:** where the capability is authored, at two times:
  - after a coupling
  - whenever a definition's `depends_on` changes
- **In an adopting project,** a methodology-shipped capability's package file is owned by core. The refresh refuses there, and a stale copy is the capability author's to fix.

```
pkit capabilities refresh <capability>
```

### Stamping a coupling

Write an entry with the coupling stamp, never by hand ([COR-044](../decisions/core/COR-044-process-authoring-layer.md)). Its flags and its refusals are the CLI reference's:

```
pkit process couple <capability>:<process-id> --state <state> --upstream <address> …
```

- **What it writes:** the entry, in the definition alone. Its upstream takes either form ("Addressing an upstream by role" above), and it carries a targeted version and a mandatory mark only when given.
- **The refresh it names.** When the capability's generated `depends-on` list is then stale, the stamp ends by naming the refresh. Run it: validation fails until the list follows the definitions ([COR-053](../decisions/core/COR-053-connection-points.md) point 4).

### The relations

The `relation` set annotates only the edges the engine cannot already see.

- **`informational`:** advisory, with no effect at run time.
- **`gates-on-readiness`:** names the edge across processes that an opaque gate predicate enforces, but declares nowhere.
- **`triggered-by`:** a coupling that something outside the engine mediates, such as a connector, and that the engine never sees. It pairs with `mode: push`.
- **`constrained-with`:** an invariant across subjects, named for visibility. The slot's first family, the existence of a hand-off, ships as checking without enforcing, through COR-042's contract, apart from `relation`. Enforcement stays deferred.

### The seam payloads

Both seams of a hand-off contract are commands that the declaring, downstream capability registers ([COR-042](../decisions/core/COR-042-process-health.md)). They run as every predicate does, under the process README's predicate runner, with one subject argument and `--json`.

- **`candidates`** runs with the subject slot carrying the contract's upstream process address, the scope it enumerates. The binding knows the trigger statically, from its own declaration.
  - It returns `{candidates: ["<id>", …]}`.
  - The source proposes. The health check confirms each id, one subject at a time, through the engine's resolution of one subject's position.
- **`resolve`** runs once for each confirmed subject, with the subject slot carrying that upstream subject's id. It returns `{downstream: ["<id>", …]}`:
  - a list that is not empty: satisfied, and fan-out is allowed
  - an explicitly empty list: a determinate absence, a missed hand-off
  - an error, or no explicit list: indeterminate, so it fails closed

### Derived edges are not relations

`composed-subprocess` and `aggregates` are deliberately not relation values.

- **Already declared.** A composition or aggregation edge is declared in full by the `subprocess` or `cascade` block, which the engine owns and resolves.
- **One home.** Stated again as an annotation, it would be a second copy of a fact whose home is that block, and the two would drift ([COR-006](../decisions/core/COR-006-artifact-roles.md)).
- **So the render derives them.** It computes the configured composite as the derived edges, read from `subprocess` and `cascade`, joined with the annotated edges of `depends_on`. Each edge is expressed exactly one way, and no edge is expressed both ways.
- **What `depends_on` is:** the layer that makes visible the edges the engine cannot see.

### `mode: push` adds no events

The position engine stays pull-only ([COR-038](../decisions/core/COR-038-process-connections.md) point 3).

- **What `push` means:** only that the edge is mediated outside the engine. The engine never pulls it, and records it for visibility alone.
- **No eventing.** No subject is created, advanced or notified by an event fired inside the engine.

### The render

The process graph draws the configured composite: the derived and the annotated edges, each labelled with its relation and mode.

```
pkit process graph
pkit connections graph
```

- **The one wiring graph.** The process graph is the process view of the one wiring graph ([COR-053](../decisions/core/COR-053-connection-points.md) point 7). The wiring graph adds the edges of offered processes, through which a `depends_on` addressed by role reaches the process that answers it.
- **Their options** are the CLI reference's, for both commands.

### Deferred

Each of these waits for a real demand ([COR-038](../decisions/core/COR-038-process-connections.md)).

- **From the first family of always-checks across subjects.** The first family of the slot for always-checks across subjects, a missed hand-off's existence, reported only, shipped through COR-042. Still deferred from it:
  - general invariants across subjects, such as mutual exclusion
  - the signals of drift and difference in data couplings
  - the inverse, orphaned artefacts
  - a trigger given as a set of states, or as "at or beyond" a state
  - remediation done automatically
- **Any coupling that enforces,** which would weigh as superseding COR-042.
