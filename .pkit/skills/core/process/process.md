---
name: process
description: Work with a process definition's shape — scaffold a new process, couple it to an upstream process, or make a hand-off checkable. Walks the substrate's authoring questions and stamps the answer through the deterministic process commands. Composite skill per COR-020; the predicate logic behind the stamps is the process-author agent's territory, not this skill's.
metadata:
  wraps_commands:
    - pkit process new
    - pkit process couple
    - pkit process hand-off
    - pkit process validate
    - pkit process health
composes:
  - new.md
  - couple.md
  - hand-off.md
gates:
  - COR-005
  - COR-008
  - COR-020
  - COR-033
  - COR-038
  - COR-042
  - COR-044
reads:
  paths:
    - .pkit/process/README.md
    - .pkit/cli/README.md
    - .pkit/schemas/_defs/process.schema.json
  records:
    - COR-016
    - COR-031
    - COR-032
    - COR-034
    - COR-035
---

# Working with a process definition's shape

This is the **process-authoring** skill. It composes the operations that declare a process's *shape* — the subject it tracks, the states it moves through, what it depends on, and which of those dependencies are checkable. Each operation asks the authoring questions, then stamps the answer through the matching deterministic command (per COR-005's skill/command pairing); the command owns correctness of the file, this skill owns correctness of the decision.

A process definition has two halves, and this skill owns exactly one of them (per COR-044):

- **The shape** — declarative data with closed vocabularies. This skill's territory.
- **The teeth** — the predicates behind every evaluable the shape declares ("how do I know a subject is in this state?", "what must be true to move?"). The stamps scaffold a fail-closed stub for each; a stub that is never implemented keeps the process honestly unreadable rather than falsely green.

So a normal authoring session is two-phase: walk the shape here, then implement the stubs. The teeth are destined for a dedicated `process-author` agent, which **has not shipped yet** — until it does, the interim route is for the author (or whichever producer the project uses) to implement each stub by hand against the predicate-runner contract in `.pkit/process/README.md`. Either way: do not write predicate logic from this skill, and when teeth-work reveals a shape problem, route it back through these operations rather than hand-editing the shape.

## Acceptance gate (run first)

Verify each record in `gates:` is `accepted`; halt if any is `proposed` or `superseded`.

- **COR-005** — skill/command pairing. Every operation here delegates its write to a command; authoring by hand instead would defeat the pairing.
- **COR-008** — git conventions, for the commit step each operation ends with.
- **COR-020** — composite-skill folder form. This skill's own shape.
- **COR-033** — the process substrate. The shape contract every question here is drawn from.
- **COR-038** — cross-process connections. The closed relation vocabulary and the coupling-in-the-subscriber rule that `couple` depends on.
- **COR-042** — the health surface and the hand-off contract that `hand-off` declares.
- **COR-044** — this authoring layer, including the shape/teeth split above and the deferred operation family below.

## Pick the operation

| Operation | When to use it | Sub-procedure |
|---|---|---|
| **Scaffold a new process** | A discipline needs its own staged, gated journey — nothing exists yet. Declares subject, states, transitions, and every evaluable's stub in one stamp. | `new.md` |
| **Couple to an upstream process** | Your process depends on another one — for readiness, for a trigger, for a shared constraint. Declares the dependency *in your own definition*. | `couple.md` |
| **Make a hand-off checkable** | An existing coupling represents work passing between processes, and you want the methodology to notice when it is dropped. Adds the evaluable contract the health surface walks. | `hand-off.md` |

The operations compose in that order for a fresh dependency: `new` (once per process) → `couple` (declare the edge) → `hand-off` (make it checkable). Each is separately re-runnable; none is a prerequisite for using another on a definition that already exists.

## Shared framing (applies to every operation)

### The shape contract is the source of truth

Every vocabulary these operations offer — cardinalities, relations, modes, wait reasons, gate kinds — is read as data from `.pkit/schemas/_defs/process.schema.json`, and the substrate's own spec for what each field *means* is `.pkit/process/README.md`. Read them; do not recite a vocabulary from memory, and do not offer the author a value the contract does not carry. When the contract grows a value, these operations pick it up with no edit here — that property is the reason the vocabularies are read rather than hardcoded, and the reason this skill has no per-relation sub-procedure.

The exact command grammar and per-flag behaviour live in `.pkit/cli/README.md`. When this skill and that document disagree about a flag, the CLI document wins and this skill is stale — say so rather than improvising.

### One definition, one owner

A process definition is an artifact of the capability that ships it. Every operation here edits **the definition its invoker owns** — never another owner's file. That is not a restriction these operations work around: per COR-038 a dependency is always declared by the *subscriber*, so wiring your process onto someone else's upstream is an edit to your own file, with theirs untouched.

If the author wants the converse — someone else's process to depend on theirs — this skill cannot do it and neither can the agent. Say so plainly and stop; that reach is an open question, not a task to improvise.

### Verify with the substrate's own checkers

Never hand-inspect a definition to decide whether it is well-formed. Use the right checker for the claim you want to make, because they answer different questions and are easy to confuse:

- **`pkit schemas validate`** — is the definition *file* well-formed against the shape contract. This is the definition lint. (The stamps already run it before writing, so a stamped definition starts clean.)
- **`pkit process status`** — where a subject *is*, by running detection predicates. Expect indeterminacy while stubs are unimplemented.
- **`pkit process validate`** — a subject's **invariants**. Not a definition lint, and it says nothing about a coupling: per COR-038 the runtime never reads `depends_on` at all.
- **`pkit process health --interpretation-only --process <address>`** — is a hand-off contract *interpretable*. This is the authoring done-signal after touching a contract. Misses are expected on a fresh contract and are never the done-signal. Always scope it to the address you just authored; the bare form walks every contract in the project, so another owner's unfinished seam would hold your signal red.

Read any green with one eye open: a report that found *nothing to check* is not the same as a clean one. Confirm the checker actually saw the thing you just authored before treating it as done. The tooling now fails closed on the two ways that used to go wrong — a stamp refuses a capability the project does not register, and a scoped health run whose address matches nothing walked reports an indeterminate scope rather than a green — but the discipline still belongs to you, because they are not the only ways a report can be about nothing.

### What this skill deliberately does not do

A family of operations is **named and deferred** per COR-016's ship-narrow discipline. Recognise the request, name the deferral, and stop — do not improvise a walkthrough. The process area's spec (`.pkit/process/README.md`) carries the authoritative list; as it stands:

- **`amend`** — evolving a definition's states or transitions while subjects are live (it rides the definition's `version` field). This is also the repair path for a coupling or contract you declared wrongly; until it ships, the interim route is a hand-edit plus a `pkit schemas validate` re-check, which `.pkit/cli/README.md` records as the one sanctioned exception.
- **Adding a wait (COR-034) or an invariant (COR-035) to an *existing* definition.** A fresh definition can declare both through `new`.
- **Subprocess embedding, cascade folds, and open regions.** The stamp has no flags for these at all — not even on a fresh definition — so they are deferred outright, and the walkthrough must not offer them. (That is narrower than COR-044 point 3 claims; the divergence is tracked and belongs to the record or the stamp, not to this skill.)

This skill ships no storyboard. Its scenarios are a walkthrough the author drives, not a scripted interaction with fixed turns; the storyboard convention pairs with agents running scripted scenarios.

### Speak at substrate altitude

The substrate tracks whatever a discipline gives it — a document through review, a room through renovation, an application through assessment. Keep your own vocabulary at that altitude (subject, state, transition, coupling, trigger, hand-off) and let the author supply the domain words; then translate their words into the contract's values yourself. A question that only makes sense for software is the wrong question here.
