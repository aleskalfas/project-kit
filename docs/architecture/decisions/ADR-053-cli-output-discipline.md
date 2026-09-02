---
id: ADR-053
title: CLI output discipline — genre-general event model, two renderers, the machine surface is the contract
status: proposed
date: 2026-09-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

pkit's CLI output grows from a read-view renderer into a **genre-general discipline**: every command emits **events** — `type`-tagged, pure-data parts from an evolving vocabulary — and a renderer selected once at the command boundary turns events into bytes. There are **two** renderers, not three: a **styled path** (the human view; the plain view is that same path with colour and width gated off, so `strip_ansi(styled) == plain` still holds) and a **`--json` serializer**. The load-bearing guarantee generalizes ADR-011 and ADR-024 into one line: **the machine surface is the stable contract** — the `--json` bytes are byte-stable across TTY / `COLUMNS` / piped and carry the full structure; the human bytes are porcelain and free to vary. This record is the generalization the ADR-006 → ADR-011 → ADR-024 line was walking toward: it consumes their principle on a new axis (genre coverage) and does not supersede them. The event vocabulary is **evolving, not closed**; its catalogue lives in a spec doc, cited here, not inventoried in this record.

## Context

ADR-006 extracted a read-view renderer (`cli_render.view()`, Option A′: data-carrying parts feed one assembler) and *deliberately excluded* the other output genera — the `install` progress dump, the `next-steps` block, and the byte-parity-pinned `status` tree — because forcing them onto the title+table+Legend shape would distort them. ADR-011 added a styling leaf and ADR-024 a wrapping leaf, each a *child* of ADR-006 consuming its renderer-owns-presentation principle on a new axis (colour; line-breaking), each a leaf that both `view()` and the hand-built procedural narratives call.

The forcing case is readability pain on exactly the excluded genera (the `install` wall, the post-init `next-steps`), and the agent-consumer reality that a stable structured surface is worth more than a prettier human one. The `.pkit/scratchpad/active/2026-08-27-cli-communication-conventions.md` note (§9 architecture, §10 decision) works the full design. The maintainer decided to build the **full** discipline — event model, vocabulary, renderers, toward a language-agnostic spec and a `cli` capability — overriding a `critic` de-scope recommendation, with the anticipation cost (one Python consumer, no second language yet) accepted with eyes open. `critic`'s durable corrections are folded as constraints below. As project-kit's own architecture record, concrete paths and the src-vs-capability split are in scope here (per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)).

## Decision

Adopt a genre-general **event model + two-renderer contract** for CLI output, generalizing ADR-006/011/024. Concretely:

1. **Events generalize ADR-006's semantic-data parts across genres.** Every output is `{type, …payload}`: `type` is a discriminated-union tag from the vocabulary; the payload is **pure data** (no ANSI, no layout); severity and render-hints are advisory attributes the renderer consumes, never data the payload holds. ADR-006's `title()` / `status()` / `section()` dicts are the first events — this record adds the `type` discriminator, a per-type payload schema, and an **extension protocol** (a new `type` implements a one-method renderable; an *unknown* `type` degrades to a structured-payload dump, never an error). This is A′ **generalized**, not Option B: the permissive unknown-type fallback is the opposite of B's "illegal states unrepresentable," so ADR-006's B-deferral and its promotion trigger stand unchanged.

2. **Two renderers, selected once at the boundary.** The **styled path** (the `style()` colour gate of ADR-011 + the `wrap()` width gate of ADR-024) produces the human view; the **plain view is that same path with both gates off** — not a second code path (a second path would drift). The **`--json` serializer** produces the machine surface. Selection is resolved once at the command boundary from `isatty` + `NO_COLOR`/`TERM` + explicit flags (`--json` / `--plain` / `--color`), exactly as colour and width already are; a string-builder never sniffs the stream. Non-TTY default is **plain**, with **`--json` opt-in** — backward-compatible, and there is no general JSON surface to default to for pkit's plain-text-script consumer.

3. **The machine surface is the stable contract (the generalized invariant).** The `--json` serializer is **byte-stable across TTY / `COLUMNS` / piped** and carries the full structure; no presentation decision reaches it. This subsumes ADR-011's `strip_ansi(styled) == plain` and ADR-024's `render_status_json` byte-stability as its two proven instances. The human surface is **porcelain** — nothing parses it, so indent, width, and colour are free to vary. Both nets are pinned as golden tests, as 011 and 024 already pin their instances.

4. **The vocabulary is evolving, not closed.** pkit's own genera break a closed core on contact (`install` = log + summary; `permissions diff` = change-preview; `status` = key-value tree). The core is a *growing* set. Its catalogue — the `type`s, their payload schemas, and the required rendering per mode — lives in a **spec doc** (`.pkit/cli/README.md` / a dedicated spec), cited here, **not inventoried in this record** (per [COR-006](../../../.pkit/decisions/core/COR-006-artifact-roles.md): the ADR carries the decision and its *why*; the doc carries the evolving *what-is*).

5. **`status` stays byte-parity-pinned.** It is migrated onto the event model only behind its existing byte-identity parity test, and is the *last* genre to move — never in the first slices. Its `--json` sibling (`render_status_json`) is already byte-stable and already conformant.

6. **The command-contract is a separate layer.** Semantic exit codes, `--help --json`, hard-fail-on-unknown-flag, and the non-interactive mutation protocol (`confirm-required` + envelope + `--confirm`) are part of the discipline but are **sequenced separately, in their own record(s)** — this ADR is the output-vocabulary/renderer layer only.

7. **Spec as we prove it; the per-language binding is an extensible seam.** The language-agnostic spec is authored *as pkit's binding proves it*, and pkit's binding is the reference implementation. The spec + a conformance suite are the contract a second-language binding would pass; the kit does **not** ship N implementations — bindings accrete per adopter-language on demand. Extraction into a `cli` capability, and the [COR-017](../../../.pkit/decisions/core/COR-017-capability-pattern.md) sub-shape extension it needs (a capability whose deliverable is a per-language adopter-imported library, not a Python script the pkit CLI runs), land on the **stability trigger** (conventions stop churning, or a second consumer / language appears) — not up front.

8. **Name the binding/spec seam now.** `cli_render.py` is the **pkit binding**; the universal half (event model, vocabulary, renderer contract, invariant, conformance) is what a future `cli` capability owns; the pkit-specific half (role→SGR palette, zone rhythm, command wiring) stays the binding. This ADR draws that line today so extraction is a lift, not a disentangling — even though extraction itself is deferred.

## Rationale

- **Why generalize, not supersede ADR-006.** ADR-006's load-bearing choices (A′ over B, tool-internal `src/` placement, the promotion trigger) are alive and are cited by ADR-011/024 as their principle-provider. Superseding ADR-006 would falsely retire those and orphan the child citations. Only ADR-006's *genre-exclusion* changes, and it changes by **honoring** ADR-006's own anti-distortion rationale (each genre gets its own event types), so it is a refinement folded in place, not a reversal.
- **Why two renderers, not three.** "Plain" is the styled path with colour and width off; the `strip_ansi(styled) == plain` invariant *is* that identity. A separate plain renderer would be a second code path that drifts — the exact failure the invariant exists to forbid.
- **Why A′-generalized, not Option B now.** Early convention churn is still model-shaped as often as layout-shaped (ADR-006's finding); the permissive discriminated union keeps changes one-place and keeps an unknown `type` from breaking a consumer. B's correct-by-construction is bought later on ADR-006's unchanged trigger, if it earns its keep.
- **Why prove on a settled genre first.** The event→bytes contract and the generalized invariant are cheapest to prove on a genre whose bytes are already re-baselined and un-pinned (a read-view), before generalizing to the churny, higher-value `install`/`next-steps` genre. The maintainer's *pain* is addressed in parallel by a leaf-level readability fix (see Implications) that needs no event model.
- **Why the spec accretes rather than ships up front.** Extracting an unproven, unshipped discipline into a multi-language contract for one Python consumer is the anticipation trap; the reference-binding-first path is [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)'s build-and-prove-then-extract applied to a cross-language contract.

### Alternatives considered

- **Whole-record supersession of ADR-006.** Rejected — retires live choices and orphans ADR-011/024 citations; only the genre-exclusion element moves.
- **An umbrella ADR that subsumes 006/011/024.** Rejected — the children's leaves (`style()`, `wrap()`) remain shipped and called; generalization stands *on* them, it does not retire them.
- **Three renderers (json / human / plain).** Rejected (`critic`) — a separate plain path drifts; plain is the styled path with gates off.
- **JSON-by-default when piped.** Rejected (`critic`) — pkit's dominant non-TTY consumer is a plain-text script/CI path; there is no general JSON surface to default to. The *event model* is the source of truth; the *default rendering* is plain.
- **A closed core vocabulary.** Rejected — pkit's own genera break it on contact; the core is a growing set behind the extension protocol.
- **Extract the capability + author the COR-017 sub-shape now.** Rejected — anticipation with one consumer; both land on the stability trigger.

## Implications

- **ADR-006 fold (maintainer sign-off).** Rule 5's "Scope boundary" bullet and the "Why scope to read-views" rationale are refined in place to reflect that the read-view was the first genre and ADR-053 generalizes the same A′ principle across genera; a forward-pointer to this record is added. No status flip; the A′-vs-B choice, the `src/` placement, and the promotion trigger stay intact.
- **ADR-011 / ADR-024 cross-ref folds.** A one-line note in each that its invariant (`strip_ansi(styled) == plain`; `render_status_json` byte-stability) is an instance of this record's generalized "machine surface is the contract."
- **Sequencing.** (0) leaf-level readability fix to `install`/`next-steps` using the existing `style()`/`wrap()` leaves — pain relief, no event model; (1) prove the event model + `--json` on a settled read-view genre, with the generalized-invariant golden; (2) generalize `install`/`next-steps` onto events; `status` migrates last behind its parity test. The command-contract layer (Decision 6) is its own later record(s).
- **Versioning.** Each output-byte shift declares a [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) changeset; no `.pkit/VERSION` edit on a branch. Not a [COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md) migration trigger (no rename / removal, no `schema_version` bump, no CLI signature break) — output bytes only.
- **Placement.** `cli_render.py` stays tool-internal, NOT propagated, until the `cli` capability extraction; the binding/spec seam (Decision 8) is drawn now.
- **Deferred COR-017 extension.** The per-language-binding capability sub-shape is a methodology gap authored at extraction, with its own `critic` / `architect` / `methodology-reviewer` pass — not part of this record.
- **Acceptance gate.** This record is `proposed`; building the event model against it, and applying the ADR-006 fold that points at it, wait on acceptance (PRJ-005).
