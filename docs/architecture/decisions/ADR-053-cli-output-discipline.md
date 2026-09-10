---
id: ADR-053
title: CLI output is a rendered data model with two contracts (machine-stable, human-porcelain)
status: accepted
date: 2026-09-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

pkit's CLI output becomes a **rendered data model with two contracts**, not per-command formatted strings: a command produces data; a renderer chosen at the command boundary turns it into bytes. There are two output **surfaces** with different guarantees — the **machine surface is the stable, versioned contract** (full structure, parseable), and the **human surface is porcelain**, free to change. This **generalizes** the accepted ADR-006 → ADR-011 → ADR-024 line to *all* output genres; it does not supersede them. The precise mechanics — the event shape, the evolving vocabulary, the renderer and selection details, the invariant tests — live in the **CLI output-discipline spec** ([the `cli` capability's output-discipline spec](../../../.pkit/capabilities/cli/output-discipline.md)), which this record governs but does not restate.

## Context

ADR-006 extracted a read-view renderer (data-carrying parts feed one assembler) and *deliberately excluded* the other output genera — the `install` progress dump, the `next-steps` block, and the byte-parity-pinned `status` tree — because forcing them onto the read-view shape would distort them. ADR-011 (styling) and ADR-024 (wrapping) each added a leaf that both the read-view assembler and the hand-built procedural narratives call.

The forcing case is readability pain on exactly those excluded genera, plus the reality that pkit's output is consumed heavily by agents and CI, for whom a *stable structured surface* is worth more than a prettier human one. The `.pkit/scratchpad/active/2026-08-27-cli-communication-conventions.md` note works the full design (problem → requirements → prior art → vocabulary → architecture). The maintainer decided to build the **full discipline**, toward a reusable `cli` capability, overriding a `critic` de-scope recommendation — with the anticipation cost (one consumer today) accepted with eyes open; `critic`'s corrections are folded as constraints below. As project-kit's own architecture record, concrete paths and the pkit-vs-capability split are in scope here (per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)).

## Decision

1. **Output is a rendered data model, generalized across genres.** A command emits *data*, not formatted strings; a renderer produces the bytes. This lifts ADR-006's data-vs-presentation split — scoped there to read-views — to *every* output genre (`install`, `next-steps`, and the rest).

2. **Two surfaces, two contracts.** The **machine surface** is the stable, versioned contract: it carries the full structure and does not change shape under presentation concerns. The **human surface is porcelain**: nothing parses it, so its wording, layout, and colour are free to change. The unstyled (plain) rendering is **derived from the human path, not a parallel renderer**, so the two cannot drift apart.

3. **Generalize, do not supersede.** This record consumes the ADR-006 → 011 → 024 principle on a new axis — genre coverage — and their choices and shipped leaves stand. Only ADR-006's *genre-exclusion* is refined, and by **honoring** its anti-distortion rationale (each genre gets its own data types rather than being forced onto the read-view shape), not reversing it.

4. **A dedicated spec doc owns the mechanics.** The event shape, the extension protocol, the evolving vocabulary, the renderer and selection details, and the invariant tests live in the **CLI output-discipline spec** ([the `cli` capability's output-discipline spec](../../../.pkit/capabilities/cli/output-discipline.md)) — an evolving reference, not frozen into this record ([COR-006](../../../.pkit/decisions/core/COR-006-artifact-roles.md): the decision and its *why* here; the *what-is* there). The vocabulary is **evolving, not closed**.

5. **Default behaviour: plain, with a machine surface on request.** When output is not an interactive terminal, the default rendering is **plain**, not the machine surface; the machine surface is requested explicitly. This is backward-compatible — pkit's dominant non-interactive consumer today is a plain-text script/CI path, and there is no general machine surface to default to.

6. **Scope and deferrals.** `status` keeps its byte-parity guarantee and migrates last, behind its existing test. The **command-contract** (semantic exit codes, machine-readable help, a non-interactive mutation protocol) is a *separate* concern with its own record(s), not part of this one. The discipline is **destined to be a reusable `cli` capability**: pkit's implementation is the reference **binding**, and extraction — plus the [COR-017](../../../.pkit/decisions/core/COR-017-capability-pattern.md) sub-shape a per-language capability needs — is **deferred** to a stability trigger (conventions settle, or a second consumer appears). The **binding-vs-spec seam** (pkit-specific realization vs the universal contract) is named now so the later extraction is a lift, not a disentangling.

## Rationale

- **Why generalize rather than supersede ADR-006.** ADR-006's load-bearing choices are alive and are cited by ADR-011/024 as their principle-provider; superseding it would falsely retire those and orphan the citations. Only its genre-exclusion moves, and it moves by honoring the same anti-distortion reasoning — a refinement, not a reversal.
- **Why two contracts, mutable-on-top.** The only way to keep a human view improvable is to *not* let anything parse it; so the stable, parseable thing is the machine surface and the changeable thing is the human view. Deriving the plain rendering from the human path (rather than a second renderer) is what prevents the two from drifting.
- **Why plain-by-default, machine-on-request.** pkit already has real plain-text non-TTY consumers and no general machine surface; defaulting non-TTY output to the machine surface would break them for uncertain gain. The *data model* is the source of truth; the *default rendering* is plain.
- **Why the spec accretes rather than ships up front.** Freezing an unproven, unshipped discipline into a multi-consumer contract is the anticipation trap; the reference-implementation-first path is [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)'s build-and-prove-then-extract, applied to a would-be cross-language contract.

### Alternatives considered

- **Whole-record supersession of ADR-006.** Rejected — retires live choices and orphans ADR-011/024's citations; only the genre-exclusion element moves.
- **An umbrella record that subsumes ADR-006/011/024.** Rejected — their leaves remain shipped and called; this generalization stands *on* them, it does not retire them.
- **A separate plain renderer (three surfaces).** Rejected — a parallel plain path drifts from the human one; plain is the human path with styling off.
- **Machine surface by default when piped.** Rejected — pkit's dominant non-interactive consumer is a plain-text script/CI path; there is no general machine surface to default to.
- **A closed, fixed vocabulary.** Rejected — pkit's own genres break a closed set on contact; the vocabulary is evolving behind an extension mechanism.
- **Extract the capability (and author the COR-017 sub-shape) now.** Rejected — anticipation with a single consumer; both land on the stability trigger.

## Implications

- **ADR-006 fold.** ADR-006's "scope boundary" (do not migrate the excluded genres) and its "why scope to read-views" rationale are refined in place to record that the read-view was the *first* genre and this record generalizes the same principle across genera; a forward-pointer is added. No status flip; ADR-006's other choices stand.
- **ADR-011 / ADR-024 cross-references.** A one-line note in each that its invariant is an instance of this record's "the machine surface is the stable contract."
- **Sequencing.** A leaf-level readability fix to `install`/`next-steps` relieves the pain first (no event model); the event model is then proven on a *settled* genre before generalizing the churny ones; `status` migrates last, behind its parity test. The command-contract layer is later record(s).
- **Versioning.** Each output-byte shift declares a [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) changeset; not a [COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md) migration trigger (output bytes only).
- **Placement.** The pkit binding stays tool-internal (not propagated) until the `cli` capability graduates; the output-discipline spec lives **inside** the `cli` capability (`.pkit/capabilities/cli/output-discipline.md`), developed on the `integration/cli-capability` branch until the capability is released.
- **Deferred capability + COR-017 extension.** Authored at extraction, with their own reviewer pass — not part of this record.
