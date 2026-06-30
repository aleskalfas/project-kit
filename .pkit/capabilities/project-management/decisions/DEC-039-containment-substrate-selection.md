---
id: DEC-039
title: Containment substrate is selectable — native sub-issues where available, textual fallback
status: accepted
date: 2026-06-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

[project-management:DEC-005-linking-and-containment] makes GitHub **native sub-issues** the canonical parent↔child mechanism, unconditionally. But not every GitHub deployment supports sub-issues — older GitHub Enterprise Server lacks them — and an operator may *deliberately* prefer the textual representation (e.g. to keep a repo consistent with a sub-issue-less work instance). On such a tracker DEC-005's "always native" contract cannot be honoured, and the parent has **no parent-side children view at all** (the native panel is absent; only the child-side textual ref + `show-tree` on demand exist).

This is the substrate-availability problem [project-management:DEC-036-substrate-pluggable-adoption] exists to solve — adapting the methodology's rules to trackers that can't express them — applied to the containment axis, which DEC-036 does not yet cover. The methodology *ideal* (native sub-issues) is correct and stays; what is missing is project-kit's adaptation when the substrate can't express it.

## Decision

**Containment becomes a selectable substrate: native sub-issues where the tracker supports them, a textual representation where it does not.** The methodology's native ideal is kept; this adds the fallback.

**D1 — Refine DEC-005 to native-*where-available*.** Native sub-issues are canonical **where the tracker supports them** (not unconditionally). Where native is unavailable, or the operator selects textual, containment uses the textual representation instead. This refines DEC-005's unconditional contract; it does **not** change the upstream methodology ideal (pm-workflow MET-004, which DEC-005 distills) — native-sub-issues-as-the-ideal stands. Project-kit's *adaptation layer* (this record + DEC-036) carries the degradation, exactly as DEC-036 degrades other distilled axes without rewriting their upstream source.

**D2 — Extend DEC-036 with a `containment` axis.** A new substrate axis in `substrate-map.yaml`: `containment: native | textual`, a **manual operator selector**. (Auto-detection of sub-issue support is explicitly deferred — see Implications.) This is the axis's first home; DEC-036's per-axis model gains a sixth axis.

**D3 — The child-side textual parent-ref is the universal spine.** It is always written, in both modes (DEC-005's textual projection). `show-tree` and every containment consumer therefore resolve children regardless of substrate; **native wins** on conflict (DEC-005's existing rule, now spanning mixed-substrate repos). The single read-seam realizing this is #345.

**D4 — Textual-mode parent-side visibility is render-on-demand, not a stored block.** Where there is no native panel, the parent-side children view is a **generated "do-not-edit" children comment** the read path refreshes (full overwrite, single source) — **not** a body block appended on every child-create. A stored block would make each child-create a read-modify-write of the *parent* body (concurrency race, partial-failure drift, a second source of truth the read-seam already derives); render-on-demand avoids all of it.

The **formal** read-seam + sole-constructor contract (the consistency invariants) is pinned in a sibling architect-owned ADR (the third sibling to [ADR-026] read-path / [ADR-031] write-path); this record decides the *rule*, the ADR the *contract*.

## Rationale

**Why adaptation, not an upstream change.** The native-sub-issues ideal is right and universal; only its *availability* varies. DEC-036 already handles "the tracker can't express this rule" for other axes by degrading project-kit-side while leaving the upstream methodology intact. Containment is the same shape, so it belongs here, not in MET-004 — keeping one source of truth for the ideal and confining the substrate-poverty handling to the adaptation layer.

**Why manual selection, deferring auto-detection.** Both substrates have a real consumer today (github.com supports native; GHES instances may not), so the selector is not speculative. But an operator *knows* their instance, so a manual `native | textual` declaration serves both cases immediately; reliable, cheap auto-detection is a convenience over it, deferred until wanted (COR-007 — earn the generality).

**Why render-on-demand over a stored children block.** The only thing a parent-side list adds beyond the child-side ref + `show-tree` is *in-UI visibility on a no-native instance*. A stored, auto-maintained block buys that at the cost of parent-body write-amplification on every child-create and a second source of truth that can drift from the read-seam. Rendering the view on demand (overwrite a generated comment) delivers the same visibility with none of those failure modes — the visibility goal and the storage decision are separable, and only visibility is wanted.

### Alternatives considered

- **Leave DEC-005 unconditional; do nothing.** Rejected: leaves GHES adopters with an inert "always native" rule and no parent-side view.
- **Change the upstream MET-004 ideal to "native where available".** Rejected: substrate-availability is project-kit's adaptation concern (DEC-036), not a change to the methodology's ideal; routing it upstream would conflate the two.
- **Stored, auto-appended `## Children` body block as the fallback.** Rejected (see Rationale): write-amplification on the parent + a second source of truth.
- **Auto-detect substrate support now.** Deferred, not rejected: manual selection serves today's consumers; auto-detection is a later convenience.

## Implications

- Realized by the merged **#344** (native write) + **#345** (the single read-seam: native-wins resolution shared by `show-tree`, the [project-management:DEC-034-cascade-slot-binding] closure-fold, and close-issue). The selector (D2) and the render-on-demand textual view (D4) are the remaining Track-2 build (EPIC #343).
- **DEC-005** gains a refinement cross-ref to this record (native-*where-available*); **DEC-036** gains the `containment` axis entry. Both stay `accepted`; the native ideal (MET-004) is untouched. The DEC-036 extension is **purely additive** — a new axis, no existing DEC-036 invariant overturned — so it needs no gate beyond the sign-off already given for refining DEC-005 + extending DEC-036.
- A sibling **ADR** (architect-owned) pins the read-seam + native-wins invariant + the textual sole-constructor; authored once this settles.
- **Deferred, not decided here:** auto-detection of sub-issue support + its per-machine sidecar cache (host-derived, keyed by instance — [ADR-032] routing), and a reconciliation back-fill for switching existing issues (a [project-management:DEC-037-adoption-ceremony] `migrate`-family op).
- **Unchanged:** [project-management:DEC-003-github-bound-substrate] (GitHub stays the bound tracker; sub-issues remain the native vocabulary).
