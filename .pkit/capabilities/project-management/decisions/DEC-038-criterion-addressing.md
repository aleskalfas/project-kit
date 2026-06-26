---
id: DEC-038
title: Address acceptance-criterion checkboxes by index with an optional text guard
status: accepted
date: 2026-06-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Every issue carries an acceptance-criteria checklist, and the close-gate refuses to close an issue while any box is unticked (the checkbox close-gate per [project-management:DEC-007-checkbox-validation]). Today the only way to tick one box is to fetch the whole issue body, flip a single `- [ ]` to `- [x]` in the text, and re-upload the entire body via `edit-issue`. That whole-body round-trip is clumsy, it invites text-surgery (`sed`/`grep`) that the permission layer then prompts on, and it risks corrupting the body on a bad edit.

The targeted checkbox-mutation verbs `check-criterion` / `uncheck-criterion` (and the field-setter `set-field`), filed as #321 (W3b of EPIC #315), replace that round-trip with a narrow operation: "tick box N on issue #M." This record decides the one design fork those verbs cannot answer for themselves — **how a caller names which checkbox to tick** — and the consistency model that keeps a narrow tick safe when the body might change between read and write.

## Decision

**D1 — Address a criterion by its 1-based index, with an optional expected-text guard.** A caller names a checkbox by its position in the acceptance-criteria list (`check-criterion 239 2` ticks the second box). A caller MAY also pass the text it expects at that position (`check-criterion 239 2 "docs updated"`); when supplied, the verb refuses to mutate unless the line at that index still matches the expected text.

The text argument is the conceptual crux of this record: **it serves two purposes at once — a wording-based way to name the box, and a guard that the box has not moved between the caller reading the list and writing the tick.** That dual role is what lets a single optional argument buy text-match's safety on top of index's simplicity. No stable per-criterion identifier is introduced and the issue-body shape is unchanged — this decision deliberately avoids a `schema_version` bump to the body structure (per [project-management:DEC-010-issue-body-minimum-structure]) and the migration that would follow.

**D2 — The verbs are intent-shaped substrate primitives, not a new layer.** They take narrow input (issue + index, never the whole body) and emit clean single-line output (a confirmation, nothing to `grep`). They are substrate primitives that refine the existing command layer of [project-management:DEC-020-methodology-as-executable-commands] — adding rows to its committed verb-subject set — not a new abstraction or a fourth layer. `check-criterion` / `uncheck-criterion` are clean substrate primitives (a single checkbox operation on an issue); `set-field` is the body/field-mutation case, which sits at DEC-020's looser GitHub-substrate tier rather than the workflow-wrapper tier — DEC-020 admits such verb-subject additions, so the layer claim holds, but `set-field` is named here as the looser fit.

**D3 — Every verb is batch-capable.** One invocation acts on N criteria (`check-criterion 239 1 3 5`); ticking five boxes is one call, not five.

**D4 — Failure and recovery is validate-up-front plus idempotent-recovery, never a transaction.** GitHub offers no multi-mutation transaction, so the verbs do not pretend to roll back. Instead they validate the entire batch *before* any mutation and abort on any hard inconsistency, then apply idempotently so a half-applied batch recovers by simply re-running. This is the capability's established house pattern (the idempotent-recovery discipline of [project-management:DEC-026-work-ownership-lifecycle]) applied to checkbox mutation. The enumerated cases:

| Case | Behaviour |
|---|---|
| Index out of range | Refuse the whole batch before mutating; report the criterion count. Never create a checkbox. |
| Expected-text mismatch at index (e.g. criteria reordered between read and write) | Refuse the affected target before mutating; report the actual line so the caller re-reads. Never tick blind. |
| Wording given but matches more than one line | Refuse; list the matches and ask for the index. Ambiguity never silently resolves. |
| Box already in the requested state | No-op success (idempotent). Ticking a ticked box is not an error. |
| Batch half-applies then faults (network) | Re-run is safe: already-applied boxes no-op, the rest complete. |
| Two writers mutate the same body at the same instant | Known limitation: last-write-wins, a tick may be clobbered. Recovery is re-tick. Not worth locking (see Rationale). |

A hard inconsistency (the first three rows) is a [project-management:DEC-014-validation-severity-model] hard-reject: the batch is refused, nothing mutates.

## Rationale

**Why index over the alternatives.** Three addressing schemes were weighed:

- *Index alone* — simplest to build and call, no body-format change, unambiguous to specify. Its one weakness is fragility: if the list is reordered between the caller reading it and writing the tick, "box 2" is now a different line.
- *Stable per-criterion id* — embed a hidden identifier on each checkbox so a tick always hits the exact box regardless of reordering or rewording. The only airtight option, but it changes how every issue body is written (touching [project-management:DEC-007-checkbox-validation], the living-document edit rules of [project-management:DEC-009-living-documents], and the body structure of [project-management:DEC-010-issue-body-minimum-structure]), forcing a `schema_version` bump and a one-time migration across every existing issue.
- *Text-match alone* — survives reordering and is self-documenting, but is ambiguous when criteria share words and brittle to small rewordings.

The decision (D1) takes index as the primary address and folds text in as an *optional guard* rather than a competing scheme. This captures index's simplicity and text's safety in one argument while paying neither the schema-and-migration cost of stable ids nor the standalone ambiguity of text-match. The fragility of bare index is mitigated exactly where it bites — the guard turns a silent wrong-box tick into a loud refusal. The robustness that stable ids would buy is not worth a migration of every issue body, because acceptance criteria are rarely reordered in practice; if a project later finds heavy criterion-reordering, stable ids remain available as a future superseding decision.

**Why validate-up-front, not transactions.** A genuine all-or-nothing execution would require compensating rollback, and the rollback can itself fail — a new failure mode the substrate cannot honour. Validating the whole batch before any mutation delivers what "all-or-nothing" actually wants (a bad target stops the operation before it corrupts anything) cleanly, and idempotent re-run covers the only residual case (a mid-apply fault) without rollback. This matches the merge-irreversibility stance already taken in [project-management:DEC-026-work-ownership-lifecycle].

**Why the concurrent-write limitation is accepted, not solved.** Simultaneous same-instant writes to one body are rare, the damage is small and visible (a box looks unticked), and recovery is a trivial re-tick. Locking would add cross-session coordination machinery far heavier than the harm it prevents. Naming the limitation is the right level of response.

## Implications

- **#321 / W3b** implements `check-criterion`, `uncheck-criterion`, and `set-field` against this addressing and failure model. The index-plus-optional-text signature and the batch shape are fixed here; the verbs add rows to [project-management:DEC-020-methodology-as-executable-commands]'s committed issue-ops set.
- **No body-schema change and no migration** follow from this record — a deliberate consequence of choosing index over stable ids. Any future move to stable ids would be a superseding decision carrying its own migration.
- **The expected-text guard reuses existing criterion extraction** — the same acceptance-criteria parsing that `show-issue --field criteria` already performs (landed in #318) identifies the line at an index and supplies the text to compare against.
- **The close-gate is unaffected** — these verbs change *how* a box is ticked, not *what* ticking means; [project-management:DEC-007-checkbox-validation]'s close-gate reads the resulting body exactly as before.
- **Tests** mirror the enumerated cases in D4 (out-of-range refusal, text-mismatch refusal, ambiguous-wording refusal, already-set no-op, half-batch re-run) and the batch path, alongside the capability's existing idempotence tests.
- **Acceptance gate.** #321/W3b builds on this record only now that it is `accepted`; authoring implementation against a `proposed` decision would have violated the gate.
