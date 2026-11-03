---
variant: specialized
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
        - src/project_kit/process_journal.py
        - .pkit/schemas/_defs/process.schema.json
        - .pkit/skills/core/process/process.md
        - .pkit/agents/core/process-author.md
      record: [COR-023, COR-033, COR-034, COR-035, COR-036, COR-038, COR-044, COR-053, ADR-020, ADR-051]
      artefact:
        - .pkit/process/shape.md
        - .pkit/process/engine.md
        - .pkit/process/connections.md
        - .pkit/process/shape.md#core-and-deferred
        - .pkit/process/shape.md#determinism-across-dynamic-structure
        - .pkit/process/engine.md#the-operations
        - .pkit/process/engine.md#the-predicate-runner-engine-contract
        - .pkit/process/engine.md#seam-ordering-contract-journal-as-intent-log
        - .pkit/process/engine.md#where-journals-live
        - .pkit/process/connections.md#the-generated-depends-on-list
        - .pkit/agents/README.md#write-carrying-categories
        - .pkit/cli/README.md#process-commands
        - .pkit/cli/README.md#process-new-capabilityprocess-id-flags
        - .pkit/cli/README.md#process-couple-addr---state-s---upstream-addr---relation-r---mode-m---why-prose---version-n---mandatory-reason
        - .pkit/cli/README.md#process-hand-off-addr---upstream-addr---trigger-state---candidates-cmd---resolve-cmd---state-s
        - .pkit/cli/README.md#process-health---process-addr---interpretation-only---json
        - .pkit/cli/README.md#regenerating-a-capabilitys-depends-on-list
        - .pkit/cli/README.md#validate
---

# Process

The process substrate is a content-free state machine that a capability binds its own staged, gated process to ([COR-033](../decisions/core/COR-033-process-substrate.md)). This README and the three pages beside it are the substrate's specification. Why a capability binds a process, and how people author one and connect it, is in [the process guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/process/README.md).

- **Who owns what.** The backbone owns the shape contract and the engine. Each capability ships its own process definition, an instance that conforms to the shape.
- **What every process gets:** a deterministic validator of each move, and a memory of where each subject stands that explains itself ("The two guarantees" below). So an agent can rely on it for "where am I, may I move, am I valid". A person with no manual can read the same answers.
- **Core and deferred.** Each part of the shape is core, shipped now, or deferred. A deferred part is named in the shape, and built only when a binding needs it ([the shape page, "Core and deferred"](shape.md#core-and-deferred)). It then gains a decision of its own.
- <a id="grounding--status"></a>**Its grounding:** [COR-033](../decisions/core/COR-033-process-substrate.md)'s implications record the bindings that proved the substrate before it shipped.

## Contents

<!-- pkit:contents -->
- [Vocabulary — one substrate, two altitudes](#vocabulary--one-substrate-two-altitudes)
- [The two guarantees](#the-two-guarantees)
- [Gate-checkability (the load-bearing rule)](#gate-checkability-the-load-bearing-rule)
- [Layout](#layout)
- [Binding a process (how a capability uses this)](#binding-a-process-how-a-capability-uses-this)
- [The authoring layer](#the-authoring-layer)
- [The pages beside this one](#the-pages-beside-this-one)
<!-- /pkit:contents -->

## Vocabulary — one substrate, two altitudes

The substrate's terms come at two altitudes ([COR-033](../decisions/core/COR-033-process-substrate.md) point 1).

- **State machine:** the content-free substrate. It holds states, guarded transitions and a position, and a journal where the project keeps one. It knows nothing about issues, screens, documents or trips.
- **Process,** the depth altitude: one discipline's journey over its own subjects, bound to the substrate. A capability authors it.
- **Orchestration,** the breadth altitude, deferred: a system of interacting processes, where one process embeds or hands off to another. It is the same substrate, one altitude up.
- **A discipline's own lifecycle artefact,** such as an issue lifecycle's `workflow.yaml`, is a process definition under this vocabulary, and keeps its own name.

## The two guarantees

The substrate gives every process two guarantees ([COR-033](../decisions/core/COR-033-process-substrate.md) point 3).

- **A deterministic validator.** Given a definition and observable reality, three answers are definite: "where is this subject", "may it move from here to there" and "is it valid". This holds even for dynamic structure ([the shape page, "Determinism across dynamic structure"](shape.md#determinism-across-dynamic-structure)).
- **A memory that explains itself.** The status view shows where the subject is, why, how it got there, and what it may do next.
  - Each comes with a live precheck, and the live precheck wins over any label in prose.
  - It renders two ways: a narrative for people, and a structured form for agents and machines.

## Gate-checkability (the load-bearing rule)

Every transition gate reduces to one of two forms ([COR-033](../decisions/core/COR-033-process-substrate.md) point 4):

- **A deterministic predicate** that the engine evaluates over the subject's artefact or domain state.
- **A recorded authorisation artefact** that the engine confirms exists, and that an authority other than the actor being gated produced. Such an artefact is a person's merge, a reviewer's verdict or a CI check.

An actor's own assertion that a gate passed is never enough. A gate that rests on judgment must leave a trace that another authority made and a check can confirm, or validation is theatre.

- **What the engine compares.** For an authorisation artefact, the engine compares the `produced_by` its predicate reports with the actor the caller names ([the engine page, "The predicate runner"](engine.md#the-predicate-runner-engine-contract)). It confirms neither.
- **So the gate holds** only where the predicate reads a trace the actor cannot write, and the caller names the actor truthfully.

## Layout

A process's parts sit in five places:

```
src/project_kit/process.py          # the engine, in the pkit binary — it does not reach a project
.pkit/process/
  README.md                         # this page: vocabulary, guarantees, binding, authoring (reaches a project)
  shape.md                          # the shape contract, field by field
  engine.md                         # the engine contract: operations, predicate runner, seam, journal
  connections.md                    # composition, the cascade fold, depends_on
.pkit/schemas/_defs/
  process.schema.json               # the shape contract as a JSON-Schema fragment (reaches a project);
                                    # capability instance schemas $ref it to inherit the shape
.pkit/capabilities/<capability>/schemas/<process-id>.yaml
                                    # each capability's own conforming process definition (instance)
.pkit/capabilities/<capability>/project/process/<process-id>/<subject>.journal.jsonl
                                    # each subject's journal, where the project keeps one
```

- **The engine** ships in the binary, as `pkit`'s `process` commands. Capabilities never implement the state machine again: they bind to it ([the engine page, "The operations"](engine.md#the-operations)).
- **The journal,** where kept, is data the project owns, committed or kept in each clone as the project chose. Its path is the engine's ([the engine page, "Where journals live"](engine.md#where-journals-live)).

## Binding a process (how a capability uses this)

A capability binds a process in four steps ([COR-033](../decisions/core/COR-033-process-substrate.md) point 2):

1. Author a process definition as the capability's own instance schema, at `.pkit/capabilities/<capability>/schemas/<process-id>.yaml`. It declares that it conforms to the shape contract, which is `../../../schemas/_defs/process.schema.json` from its folder.
   - Author it through the authoring layer below, not by hand, since the stamps own the file's correctness.
   - The one exception is a block no stamp writes yet ("Deferred authoring operations" below). Such a block is written into the definition by hand.
2. Drive it through the capability's commands, each named by a verb and a subject, which call the engine ([the engine page, "Seam-ordering contract"](engine.md#seam-ordering-contract-journal-as-intent-log)).
3. Address the process elsewhere as `<capability>:<process-id>`.
   - A parent embeds it by that address, through a `subprocess` state ([COR-036](../decisions/core/COR-036-process-composition.md)).
   - When its capability offers it under a role, another definition's `depends_on` may address it by role instead, as `<publisher>::<role>:<point>` ([COR-053](../decisions/core/COR-053-connection-points.md)).
   - Orchestration, a concurrent hand-off, stays deferred.
4. When a definition's `depends_on` changes, run `pkit capabilities refresh <capability>`, so that the package's generated `depends-on` list follows it ([the connections page, "The generated `depends-on` list"](connections.md#the-generated-depends-on-list)). `pkit validate` fails until it does.

The schema-binding grammar is unchanged ([COR-023](../decisions/core/COR-023-schema-binds-inline.md)). Capabilities stay independent peers that describe themselves.

## The authoring layer

Authoring a definition does not mean knowing these pages by heart. The layer has three tiers, split by the kind of work each does ([COR-044](../decisions/core/COR-044-process-authoring-layer.md)). A definition's shape is declarative data with closed vocabularies, so a procedure can walk it. Its teeth are logic over the owner's reality, which takes judgment.

- **The commands,** `pkit process new`, `pkit process couple` and `pkit process hand-off` ([the CLI reference, "Process commands"](../cli/README.md#process-commands)):
  - They are deterministic stamps. They scaffold and change the definition, and validate every value against the vocabularies, read as data from the shape contract, `.pkit/schemas/_defs/process.schema.json`.
  - They scaffold a predicate stub that fails closed for each declared evaluable, and register it in the owning capability's package.
  - Each needs an owning capability that the project registers as a component, the same set that contract discovery walks. So a stamp can never write a definition that nothing watches. The CLI reference specifies the grammar, and that refusal.
  - A stamp also refuses a capability whose files the project receives as synced copies, such as one the methodology ships.
  - `pkit process health --interpretation-only --process <address>`, scoped to the definition, is the read-only check that pairs with them. It reports each hand-off contract it cannot interpret, a seam still a stub among them, and counts no missed hand-off.
  - That check reads hand-off contracts alone. A definition that declares none passes it, whatever stubs its states and gates still hold.
- **The `process` skill:** the walkthrough over those commands.
  - It asks the shape questions, and then stamps the answer. The questions are what the subject is, what each state means and which moves are gated. They also ask whether a trigger is stable, and whether a candidate source would fail loudly or return empty.
  - It also owns the judgment the stamps refuse on purpose. It routes an adopter with no owning capability through capability authoring first.
- **The `process-author` agent:** the teeth, the predicates behind every evaluable the shape declares. They are detections, gates, entry guards, `resume_when`, invariant checks and both seams of a hand-off.
  - It turns the owner's intent, given in plain words, into predicates that satisfy the predicate-runner contract ([the engine page, "The predicate runner"](engine.md#the-predicate-runner-engine-contract)). Each is read-only and fails closed, and answers about the one subject it was given.
  - It finishes with the same check, scoped to the definition it worked on.
  - A problem of shape it uncovers goes back through the skill's operations, never fixed by hand. Registering a predicate stays with the commands.
  - Stubs fail closed until they are written, so an unwritten predicate reads as indeterminate, never green.

**Its write authority is yours to grant.** The agent owns exactly one overlay category, `process-authoring-targets` in the project's agents overlay ([the agents README, "Write-carrying categories"](../agents/README.md#write-carrying-categories)). The category ships as an explicit empty list.

- **What the agent owns:** nothing, until the project lists its own definition files and predicate-script locations there, one file at a time.
- **What it can never own:** content that sync manages. The deploy refuses an entry that resolves into it, and names the path, so a methodology-shipped definition can never enter the grant.
- **One definition for each invocation:** a discipline of the agent's body, not metadata.

**Deferred authoring operations.** This list is the authoritative one, and the `process` skill points here:

- **`amend`:** evolving states or transitions under live subjects, riding the definition's `version`. It is also the way to repair a coupling or a contract that was declared wrongly.
- **Adding a wait or an invariant to an existing definition** ([COR-034](../decisions/core/COR-034-human-pause-gate.md), [COR-035](../decisions/core/COR-035-process-invariants.md)). A fresh definition declares both through `pkit process new`.
- **Subprocess embedding, cascade folds and open regions,** the three blocks of structural composition. No stamp writes them in any definition, fresh or not ([COR-044](../decisions/core/COR-044-process-authoring-layer.md) point 3). Each lands when a real authoring case needs it.
  - The deferral is of authoring alone. The substrate resolves all three at run time today, so a definition that carries one behaves as these pages describe.
  - What is missing is the grammar of flags that would stamp it.

## The pages beside this one

Each part of the substrate is described here, or on one of the pages beside this one:

- [`shape.md`](shape.md) — what a process definition declares, field by field: the subject, detection modes, waits, invariants and dynamic structure.
- [`engine.md`](engine.md) — the engine's operations, the predicate runner, the seam-ordering contract and the journal.
- [`connections.md`](connections.md) — composition, the cascade fold and `depends_on`.

**Where each section that left this page went:**

- <a id="the-shape"></a>"The shape" is [`shape.md`, "The fields"](shape.md#the-fields).
- <a id="subject-cardinality-core"></a>"Subject cardinality" is [`shape.md`, under the same heading](shape.md#subject-cardinality-core).
- <a id="blocked--a-first-class-wait-core"></a>"Blocked — a first-class wait" is [`shape.md`, under the same heading](shape.md#blocked--a-first-class-wait-core).
- <a id="invariants--position-independent-always-checks-core"></a>"Invariants — position-independent always-checks" is [`shape.md`, under the same heading](shape.md#invariants--position-independent-always-checks-core).
- <a id="determinism-across-dynamic-structure-deferred"></a>"Determinism across dynamic structure" is [`shape.md`, under the same heading](shape.md#determinism-across-dynamic-structure).
- <a id="composition--cross-process-outcome-resolution-core"></a>"Composition" is [`connections.md`, under the same heading](connections.md#composition--cross-process-outcome-resolution-core).

The sections that other text names by their headings stand below, each leading to its new home.

### Detection modes (core)

The detection modes, and how the engine reads each, are [`shape.md`'s "Detection modes"](shape.md#detection-modes-core).

### Cascade — fold one child process's member outcomes (core)

The cascade fold is [`connections.md`'s "Cascade"](connections.md#cascade--fold-one-child-processs-member-outcomes-core).

### depends_on — inert cross-process connection metadata (core, COR-038)

`depends_on`, the mandatory mark and the generated `depends-on` list are [`connections.md`'s "depends_on"](connections.md#depends_on--inert-cross-process-connection-metadata-core-cor-038).

### The engine

The engine's operations, its predicate runner, the seam-ordering contract and the journal are [`engine.md`](engine.md#the-operations).

### The predicate runner (engine contract)

The contract every predicate satisfies is [`engine.md`'s "The predicate runner"](engine.md#the-predicate-runner-engine-contract).

### Seam-ordering contract (journal-as-intent-log)

The order in which a capability's wrapper applies its side-effect and journals a move is [`engine.md`'s "Seam-ordering contract"](engine.md#seam-ordering-contract-journal-as-intent-log).

### The journal — optional audit (COR-033 point 7)

The journal, its setting and its ignore rules are [`engine.md`'s "The journal"](engine.md#the-journal--optional-audit-cor-033-point-7).
