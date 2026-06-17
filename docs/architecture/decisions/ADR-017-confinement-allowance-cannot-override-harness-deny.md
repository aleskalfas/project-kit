---
id: ADR-017
title: A confinement-toolkit allowance adds reach within what the harness permits; it cannot override a harness-built-in deny
status: accepted
date: 2026-06-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

A consumer project hit an in-sandbox `pnpm install` failure: a third-party package vendored a stray `.idea/` folder inside its npm tarball, and the Claude Code harness's built-in protection of VCS/IDE metadata (`.idea`, nested `.git`) denied the write — so install EPERM'd under the box. The proposed fix (in the originating hand-off note and in my own earlier analysis) was a `node` confinement-toolkit `allow-write` that re-allows writes inside `node_modules`, on the assumption that a more-specific `allow-write` overrides the harness deny.

**A fresh-session spike has disproved that assumption.** A confinement-toolkit `allow-write` can *add* allowances on top of what the harness permits, but it **cannot override a harness-built-in deny**. The harness's `.idea`/`.git` protection sits *above* `allow-write` and wins. So the proposed `node`-toolkit re-allow would not work, and pkit must not ship it.

The honest picture this ADR records: the JS-install over-fire is **not pkit-fixable** by a toolkit re-allow; the real fix is **harness-side** (Claude Code scoping its metadata protection to the authored repo root rather than policing downloaded `node_modules`); and the **interim adopter workaround** is to run *install* unconfined via the `sandbox exclude` widening gesture, accepting honestly that install — the riskiest op — runs outside the box under that workaround.

This bounds the [ADR-008](ADR-008-confinement-allowances.md) / [ADR-015](ADR-015-command-declared-network-egress.md) confinement-toolkit model with a general boundary: the toolkit's `allow-write` / `allow-host` allowances are **additive within what the harness permits, never overrides of a harness-built-in deny.**

## Context

The forcing question (issue #85, under EPIC #84) came from a consumer project (a trip-planner app workstream): agents could not run the JS package-manager toolchain (`pnpm`/`npm`) **inside the OS sandbox**. The originating hand-off note (`trip-planner-agent-app/.pkit/scratchpad/active/2026-06-17-node-toolchain-confinement.md`) traced one of the two failures to the harness protecting VCS/IDE metadata: a transitive dependency (`iconv-lite@0.6.3`) vendors a `.idea/` folder in its tarball, so install's create/unlink of `node_modules/.pnpm/iconv-lite@.../.idea/**` EPERMs under the box.

That note — and the earlier architectural analysis I produced on the same proposal — recommended completing the `node` confinement-toolkit with a project-relative `allow-write` (effect `narrowing`) for `node_modules`/`.pnpm-store`, **resting on one untested assumption**: that a more-specific `allow-write` on the tool-managed tree *overrides* the harness's `.idea`/`.git` bare-name deny. The note flagged this assumption as the single thing that could only be settled by a fresh-session run, because the OS sandbox profile is frozen at session start and never hot-reloaded — a session that predates the projection keeps enforcing the old profile, so the staged re-allow was applied but unverified.

The spike has now returned. It ran in a **provably fresh** box (a canary check: a normally-denied path `~/.cache/pkit-spike-canary` was added to `allowWrite` and wrote successfully — so the box demonstrably loaded the new config, ruling out the stale-profile confound the note warned about). In that same fresh box, with `node_modules` present in the active `allowWrite`, writes to `.idea` and to nested `.git` **inside** `node_modules` were **still DENIED**. The assumption is disproved: the re-allow loaded, and the harness deny still won.

This ADR records that finding. As project-kit's own architecture-decision record, harness and platform specifics are in scope here, unlike the harness-neutral COR. It is a faithful application of the spike-pinned-by-evidence discipline established in [ADR-014](ADR-014-macos-sandbox-platform-stance.md): the spike caught a false assumption before a broken toolkit shipped. Status `proposed` is the acceptance-gate gesture per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md).

**Measured harness deny surface (the evidence).** A probe wrote marker files at representative paths, unsandboxed (baseline) and under the agent OS sandbox in the fresh session:

| Path | Under the box |
|---|---|
| Canary: a normally-denied path added to `allowWrite` | **ALLOWED** (proves the box loaded the new config — session is fresh) |
| `.idea` (anywhere, incl. inside `node_modules`) | **DENIED** |
| nested `.git` internals inside `node_modules` | **DENIED** |
| `.git` at the **real repo root** | **ALLOWED** (git ops need it) |
| `node_modules` itself (plain writes) | **ALLOWED** by default (workspace) |
| a planted git hook inside `node_modules` | **did not execute** (confinement teeth hold) |

Two things this surface establishes. First, the deny is **asymmetric** — not "bare-name `.git`/`.idea` everywhere": repo-root `.git` is writable, `.idea` is denied everywhere, nested `.git` is denied inside `node_modules`. Second, and decisively: an `allowWrite` covering `node_modules` does **not** lift the `.idea`/nested-`.git` deny within it. The harness protection is *above* `allow-write` in the resolution order.

## Decision

**A confinement-toolkit allowance is additive within what the harness permits; it cannot override a harness-built-in deny.** Three things follow.

**1. The JS-install over-fire is NOT pkit-fixable via a `node`-toolkit re-allow. Do not ship one.** An `allow-write` on `node_modules`/`.pnpm-store` cannot defeat the harness's `.idea`/nested-`.git` deny (measured — the re-allow loaded and the deny still won). Shipping such a toolkit entry would advertise a fix that does not hold: the adopter would believe install works in-box because the toolkit "covers" `node_modules`, while install still EPERMs on the vendored `.idea`. That is the believed-but-absent-boundary failure [ADR-004](ADR-004-autonomy-intent-confinement.md) rule 4 and the [COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) honesty discipline forbid, inverted: a believed-but-absent *capability*. The `node`-toolkit re-allow is therefore **not** built. This corrects the originating hand-off note's recommendation and my own earlier analysis, both of which assumed the override worked.

**2. The real fix is harness-side, and pkit cannot file it — record it as an upstream follow-up.** The correct resolution is for Claude Code to scope its `.git`/`.idea` protection to the **authored repo root** and stop policing the contents of downloaded `node_modules`. The protection is right for the developer's own repo metadata; it over-fires on vendored junk inside third-party packages. This is the preferred end-state, but it lives outside pkit's reach (it is harness behaviour, not pkit configuration). It is recorded here as a tracked upstream follow-up — the analogue of [ADR-014](ADR-014-macos-sandbox-platform-stance.md)'s "prefer a fixed `uv` over the exclusion if one ships."

**3. The interim adopter workaround is the `sandbox exclude <package-manager>` widening gesture — loud, explicit, honest about its cost.** Until the harness fix lands, an adopter who needs in-box JS install runs the package manager *unconfined* via `sandbox exclude <package-manager>` — the [ADR-008](ADR-008-confinement-allowances.md) rule 4 widening path (loud, never-auto, never-committed, always-reported). Ongoing agent work stays boxed; only the install step runs outside. A project-local pnpm store (`store-dir=.pnpm-store` → `<project>/.pnpm-store`) is writable by default (no grant needed), so the store half of the original problem is a non-issue and needs no toolkit entry. **The honest trade must be stated, not hidden:** install — the riskiest operation (it runs third-party postinstall scripts, the top supply-chain vector) — runs unconfined under this workaround. That is acceptable only as a *temporary, explicit* operator gesture, never as a pkit default and never auto-applied. It is strictly worse than an in-box install; it is better than disabling the sandbox wholesale, because ongoing agent work stays confined.

## Rationale

**Why the assumption had to be measured, not reasoned.** Filesystem-deny resolution order between a harness-built-in protection and an operator/pkit `allowWrite` is a harness-internal fact with no documented contract pkit could rely on. The hand-off note correctly isolated it as the one load-bearing unknown and refused to let the staged re-allow count as verified, because the frozen-at-session-start sandbox profile means a non-fresh run reproduces the *baseline*, not the fix. The canary is what makes the spike trustworthy: without it, a DENIED result is ambiguous (deny wins, *or* the box never loaded the re-allow); with the canary writing successfully, the box provably loaded the new config, so the surviving deny is the harness winning — not a stale profile. This is the spike-pinned-by-evidence discipline ADR-014 set: settle the harness-internal fact against the live box, in a session you can prove is fresh, before building on it.

**Why not ship the toolkit anyway "in case it helps."** A toolkit entry that does not lift the deny is not inert — it is misleading. `sandbox toolkit show node` would render an `allow-write` for `node_modules` classified `narrowing`, implying the box is now usable for Node install, while install still fails on the vendored `.idea`. The whole point of the [ADR-008](ADR-008-confinement-allowances.md) narrowing class is "makes the box usable" — an entry that does not make the box usable for its stated purpose violates the classification's meaning. The honest move is to *not* ship the entry and to record *why* (this ADR), so the next person who reaches for the obvious re-allow finds the disproof instead of re-deriving it.

**Why `sandbox exclude` and not a quieter mechanism.** No quieter mechanism exists that works: `allow-write` cannot override the deny (the finding), and there is no harness hook to scope the protection from pkit's side. `excludedCommands` is the only built-in escape, and it widens — so it rides ADR-008 rule 4's loud/explicit/never-auto/never-committed/always-reported path without exception. Pretending the workaround is narrowing (auto-applicable) would silently run install unconfined for every Node adopter — the exact §49 trap. Excluding only the install command, named for the operator to run deliberately, is the minimal honest widening.

### Alternatives considered

- **Ship the `node`-toolkit `allow-write` re-allow as recommended in the hand-off note.** Rejected on the spike — the re-allow loaded (canary-proven) and the harness `.idea`/nested-`.git` deny still won. The entry would not fix install and would mislead `toolkit show` into implying it does.
- **A "keep `.git`-internals denied, allow everything else in `node_modules`" narrower variant.** Moot — the blocker is `.idea` (denied everywhere) and nested `.git`, both above `allow-write`; no `allow-write` shape lifts them. The narrowness of the variant changes nothing about the resolution order.
- **Treat the harness deny as a pkit `denyRead`/`denyWrite` collision to be reconfigured from pkit's side.** Rejected — the protection is a harness built-in, not an entry in the pkit-authored `sandbox` block; pkit's single sandbox-block writer ([ADR-008](ADR-008-confinement-allowances.md) rule 2) cannot reach it. The lever does not exist on pkit's side.
- **Auto-apply `sandbox exclude` for the package manager so Node adopters get in-box install transparently.** Rejected — exclusion widens (install runs unconfined); auto-applying a widening allowance is forbidden by [ADR-008](ADR-008-confinement-allowances.md) rule 4 and [ADR-004](ADR-004-autonomy-intent-confinement.md) rule 4. It is named for the operator, never auto-applied.
- **Disable the sandbox for the whole session to unblock install.** Rejected — it forfeits confinement for *all* agent work, not just install. The `sandbox exclude` workaround keeps ongoing work boxed and isolates the unconfined window to the install command.

## Implications

- **Bounds ADR-008 and ADR-015 in place; supersedes nothing.** This records the general boundary of the confinement-toolkit model: `allow-write` and `allow-host` are **additive allowances within what the harness permits — never overrides of a harness-built-in deny.** [ADR-008](ADR-008-confinement-allowances.md)'s narrowing/widening/narrowing-but-reported postures and [ADR-015](ADR-015-command-declared-network-egress.md)'s `allow-host` egress surface all sit *under* the harness's own deny floor; none can lift it. The boundary-effect organising principle stands unchanged — this names a ceiling the model already had implicitly.
- **No `confinement-toolkit.yaml` change.** The `node` toolkit is **not** completed with a `node_modules`/`.pnpm-store` re-allow — it would not work. This ADR is a record only; it sanctions *not* building the toolkit entry the hand-off note proposed.
- **No migration.** No file/directory rename or removal in a kit-owned tree, no `schema_version` bump, no CLI signature change, no capability subtree restructure. `pkit migrations check-diff --include-working-tree --base main` is expected clean. This is a decision record, not a surface change to an installed adopter's state.
- **The harness-side fix is an upstream follow-up pkit cannot file.** "Scope `.git`/`.idea` protection to the authored repo root; stop policing `node_modules` contents" is the preferred end-state, tracked here as the analogue of ADR-014's fixed-`uv`-version-floor follow-up. pkit records it; the harness vendor closes it.
- **The interim workaround is documented as the `sandbox exclude` widening gesture.** It runs install unconfined (the honest cost), keeps ongoing agent work boxed, and needs no toolkit grant for the store (a project-local `.pnpm-store` is writable by default). It rides ADR-008 rule 4 exactly: loud, never-auto, never-committed, always-reported.
- **The originating hand-off note's recommendation and my earlier analysis are corrected.** Both assumed the `allow-write` override worked. The spike disproved it; this ADR is the corrected record. The consumer-side stopgap (project-local store + `dangerouslyDisableSandbox` / install bypass) remains the adopter's interim path until the harness fix lands — now reframed around `sandbox exclude` for the install command rather than a toolkit re-allow.
- **No version bump in this change-set.** A newly-recorded confinement boundary is a surface change per [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md), but the bump is left to lifecycle time (the maintainer runs the acceptance gate and the version bump together); this change authors the ADR file only, `status: proposed`.
