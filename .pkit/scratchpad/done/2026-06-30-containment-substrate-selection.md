---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-30
retired: 2026-06-30
produced:
  - '#342'
  - '#343'
---

# Containment substrate selection — native sub-issues vs textual children-list

Design exploration. Retires by producing a DEC refinement (DEC-005 / DEC-036) + an EPIC. Not built yet.

## Problem

How a parent's children are collected and displayed depends on a substrate not every tracker has:

- **DEC-005 (accepted)** makes **GitHub native sub-issues** the canonical containment — GitHub collects + displays children under the parent (native panel + Projects v2 "Sub-issues progress"). But the sweep found native sub-issue linking **only in the decisions, never the scripts** — `create-issue` writes only the textual child-side parent-ref; `show-tree` reconstructs children by parsing those refs. So DEC-005's canonical mechanism is **accepted but unimplemented**, and there is **no parent-side children collection** today except `show-tree` on demand.
- **Not all GitHub instances support sub-issues** (GHES — e.g. github.ibm.com — only in recent versions). So native can't be assumed; a textual fallback is required.
- Operators want to **choose** the substrate: use native where available, but also *deliberately* stay on textual (e.g. keep this repo consistent with a GHES work project that lacks sub-issues), and **switch to native later** (for new issues) when the instance gains the feature.

This is exactly DEC-036's substrate-pluggability, applied to the containment axis.

## Decision direction (operator-chosen)

A **config-driven containment-substrate selector**, native-primary with a textual fallback, both UI-visible.

- **D1 — Selector in `substrate-map.yaml`** (DEC-036's home): `containment: auto | native | textual`.
  - `auto` → auto-detect sub-issue support on the instance and resolve to native/textual.
  - `native` → force native (warn/degrade if the instance lacks it).
  - `textual` → force the body-text list even where native is available (the deliberate-consistency case).
- **D2 — Auto-detection** probes the instance's sub-issue capability once, seeds the resolved value (cached to avoid per-call probing); the operator can override manually at any time. Manual override always wins.
- **D3 — Native mode** implements the DEC-005 gap: `create-issue` (and any parent-link mutation) sets the native `parent`/`subIssues` GraphQL fields. Parent-side collection = GitHub's native panel + Projects "Sub-issues progress". No body-text list.
- **D4 — Textual mode**: `create-issue --parent` appends the child to a maintained **`## Children` block in the parent body** (UI-visible on GHES, where there is no native panel); a `check-criterion`-style verb (`add-child` / `remove-child`, or generalized) edits the block so the agent never hand-edits the description. Parent-side collection = the body-text block + `show-tree`.
- **D5 — Universal spine**: the **child-side textual parent-ref is always written** (both modes), so `show-tree` can derive the tree regardless of substrate. **Native wins** on conflict (DEC-005); the textual artifacts are the projection/fallback, never authoritative over a present native link.
- **D6 — `show-tree` reads both**: native sub-issues where present, textual refs / body-text block otherwise — so a **mixed-mode** repo (some issues created under each mode after a switch) renders correctly.
- **D7 — Switch is forward-looking**: changing the selector affects *new* issues; existing issues keep their representation. An optional back-fill (DEC-037 `migrate`-family, enumerate→cite→confirm→apply) can reconcile old→new later — separate, not v1.

## Carriers

- Refines **DEC-005** (implement native sub-issues; add the availability/selector/fallback dimension; pin native-wins across the mixed-mode case).
- Extends **DEC-036** (containment becomes a selectable substrate axis with auto-detect + manual override, alongside priority/type/workstream/state/hierarchy).
- An **EPIC** for the build: native-linking impl · capability auto-detection · the selector config + resolution · the textual `## Children` block + its maintenance verb + `create-issue` auto-append · `show-tree` dual-read · (deferred) the reconciliation back-fill.

## Open questions (for critic / architect)

- **Selector home + shape:** `substrate-map.yaml` `containment:` axis (consistent with DEC-036) vs `config.yaml`. Ternary like DEC-036's other axes (bound / unsupported / absent)? How does `auto`'s detected value persist without becoming a second source of truth?
- **Auto-detection mechanism:** how to probe sub-issue support reliably + cheaply (GraphQL feature probe? a one-shot cached capability check), and where the cache lives (per-machine vs committed — ADR-029/032 routing applies: detected capability is host/instance-derived → per-machine?).
- **Mixed-mode honesty:** after a forward switch, old children sit in the body-text block while new ones are native — `show-tree` reconciles, but the parent's *UI* shows children split across the native panel and the `## Children` block until a back-fill runs. Acceptable? Surface loudly?
- **Is the `## Children` block a DEC-036 "degradation representation"** (consistent, the textual analogue of native sub-issues) or a new body-format convention needing its own justification + body-format.yaml entry? Likely the former.
- **DEC-005 native-wins vs a stale body-text block:** reconciliation rule when an issue has both (e.g. switched modes) — native authoritative, body-text block rewritten/ignored.
- **COR-007 scoping:** native-impl and textual-fallback are *both* real today (github.com supports native; github.ibm.com/GHES doesn't) — two real consumers, so neither is speculative. But cap the v1 (selector + both modes + show-tree dual-read); defer the reconciliation back-fill.

## Reshaped after critic + architect (2026-06-30) — the settled v1

Both reviewers converge: **split**, shrink, and gate.

- **Track 1 — implement native sub-issues (DEC-005 gap), FIRST and unconditional, as its own change.** No selector, no `auto`, no new decision — it's overdue correctness debt on an accepted DEC. Delivers the github.com native children panel for free + the Projects "Sub-issues progress". `show-tree` reads native-where-present, child-side-ref otherwise — **resolved through ONE containment read-seam** (ADR-026 pattern), native-wins as a *seam invariant*, NOT logic scattered in `show-tree` (the closure-fold child-walk would otherwise re-derive and drift).
- **GHES in-UI children — prefer RENDER-ON-DEMAND over a stored block.** The stored `## Children` block reintroduces the failure mode DEC-005 designed out (every child-create becomes a read-modify-write of the *parent* body → concurrency race, partial-failure drift, a second source of truth `show-tree` already derives). Instead: a generated **"do-not-edit" children comment** the seam refreshes (full overwrite, not an append) — UI-visible on GHES, single-source, no write-race. If a stored block is ever truly required, it must be a *conditional degradation section* (not a universal `body-format.yaml` required section) written through a **sole-constructor** (ADR-031 discipline), idempotent by value-equality (DEC-026).
- **Selector: manual `native|textual` intent in `substrate-map.yaml` (new `containment` axis); DEFER `auto`.** `auto` is the one speculative piece (cheap/reliable detection unproven). When added: the *intent* lives in the committed map; the *resolved* capability is a **non-authoritative per-machine sidecar cache** (ADR-032 Rule A host-derived + Rule B pkit-owned → `runtime_ignore` sidecar), keyed by **instance/remote** (a machine may have github.com + GHES repos), never written back into the map (ADR-026 one-consumer-contract).
- **Defer the reconciliation back-fill** to a DEC-037 `migrate`-family op (re-validate-at-apply, value-equality idempotency, auditable report).

### Carriers + the gate
- A **DEC** refining DEC-005 (native-canonical-*where-available*, not -always) + extending DEC-036 with the `containment` axis (its 6th). This **modifies an accepted foundational contract** + adds a settled-model axis → **maintainer sign-off required** (parity with DEC-036's DEC-003 partial-supersession sign-off), with the supersession gesture.
- A sibling **containment-contract ADR** (read-seam + native-wins invariant + the sole-constructor for any block write) — architect owns it, authored once settled + signed off.
- **Track 1 (implement native) needs none of this gate** — it's implementing accepted DEC-005; it can proceed immediately.

### v1 cut (dependency order)
1. native-impl (unconditional) + `show-tree` dual-read via the seam. ← no gate
2. manual `native|textual` selector (`substrate-map.yaml`) + textual mode's render-on-demand children comment. ← gated on sign-off
3. `auto`-detection (sidecar cache) — fast-follow, not v1.
4. reconciliation back-fill — deferred.

## Relationship to existing work

DEC-005 (canonical native sub-issues — implement the gap), DEC-036 (substrate-pluggability — extend with the containment axis), DEC-003 (GitHub-bound substrate — sub-issues stay the native vocabulary), DEC-037 (the optional reconciliation back-fill is a `migrate`-family op). Sibling concern to the trust-workspace (#341) substrate-portability theme, but distinct.
