---
id: ADR-014
title: macOS autonomy is supported via an in-box zero-dep hook plus an OS-box exclusion for the uv-shim CLI
status: accepted
date: 2026-06-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

[COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md) makes permissions a harness-neutral model with an explicit *honesty-about-gaps* discipline: a realizer declares which dimensions its harness enforces natively and reports the residual gap rather than overstating fidelity. [ADR-004](ADR-004-autonomy-intent-confinement.md) split agent autonomy into intent × confinement and delegated the confinement axis to the OS sandbox (macOS Seatbelt / Linux bubblewrap), claiming filesystem confinement is "genuinely native." [ADR-008](ADR-008-confinement-allowances.md) added the confinement-allowance surface and rested on the premise that pkit's own runtime "runs fine in the box once `uv` is accommodated" (the build-cache `narrowing` allowance). [ADR-002](ADR-002-permission-realizer-ownership.md) / [ADR-003](ADR-003-permission-core-code-home.md) pin the **same-code invariant**: the PreToolUse hook and `pkit permissions diff` must reach identical decisions from one `decide()` core, which forces the hook to be code an in-tree script can run without the global `pkit` runtime.

Both ADR-004's "genuinely native" claim and ADR-008's "runs fine once accommodated" premise were written platform-agnostically. This ADR (issue #19, under EPIC #18) records the **macOS platform stance** that emerged when those claims were tested against a genuinely-confined Claude Code session. It is the platform-conditional qualifier on ADR-004's confinement claim and the correction to ADR-008's accommodation premise.

**Evidence — established in a forced Seatbelt-confined session** (`sandbox.enabled: true` + `failIfUnavailable: true`, so the box was provably active, not silently fail-open):

1. A write outside the workspace was **denied** (probe BLOCKED) — confinement genuinely active.
2. `uv` first failed on its **cache** (`~/.cache/uv` denied); accommodating the cache (the ADR-008 `narrowing` allowance) got past that.
3. With the cache allowed, `uv` 0.9.8 then **panicked at the SystemConfiguration proxy probe** (`uv-0.9.8/crates/uv/src/lib.rs:2432`, "Attempted to create a NULL object" — an `SCDynamicStore` mach-service denial).
4. `UV_OFFLINE=1`, `ALL_PROXY=…`, `NO_PROXY=*` / empty-proxy, and combinations **all still panicked** — the proxy probe fires unconditionally at reqwest client construction, independent of offline mode or proxy env. **No env lever fixes it.**
5. The `SCDynamicStore` mach-service denial is a **fixed, non-configurable** part of Claude Code's Seatbelt profile (confirmed against the harness sandbox docs). `excludedCommands` is the only built-in escape — and it *widens* (the command runs fully unconfined).
6. Side-finding (feeds #21): without `failIfUnavailable: true`, Claude Code **silently runs unconfined** when the box cannot initialize — so `pkit permissions sandbox enable` was advertising confinement that did not hold.

The decision below is settled — evidence above plus operator sign-off — and recorded `accepted` per the [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md) acceptance gate. As project-kit's own architecture-decision record, harness and platform specifics are in scope here, unlike the harness-neutral COR.

## Decision

**macOS autonomy IS supported.** The unsupported-platform alternative is rejected; autonomy stands on macOS via a two-part mechanism that splits enforcement from confinement honestly.

**1. Enforcement runs in-box — the permission hook is a zero-dependency `python3` script.** The PreToolUse hook drops its `uv run --script` shebang (and PEP-723 `ruamel.yaml` dependency) and runs under the system `python3` interpreter that exists in every Seatbelt box. The hook's decision logic is already dependency-free; the only third-party reach is the YAML loader, so the shared loader (`.pkit/permissions/`) gains a **stdlib YAML-subset fallback** used when `ruamel.yaml` is not importable. Because both the hook and the `pkit permissions` CLI import that *same* loader and the *same* `decide()`, the same-code invariant of ADR-002 / ADR-003 is preserved — the fallback is one code path both callers reach, not a second `decide()`. Per-tool-call enforcement therefore keeps working under Seatbelt, where `uv` cannot run.

**2. The `pkit` / `uv` CLI is excluded from the OS box.** Because `uv` cannot run confined under Seatbelt (the fixed `SCDynamicStore` denial, no env lever — evidence 3–5), the `pkit`/`uv` command is placed in `excludedCommands`: it runs **unconfined** by the OS box, but **remains gated by the permission hook** (intent enforcement is unaffected by the OS-box exclusion). This is a *widening* allowance in ADR-008's classification, and the [ADR-008](ADR-008-confinement-allowances.md) discipline holds without exception: the exclusion is a **loud, explicit, never-silent** gesture. `setup autonomy` **names** the required `sandbox exclude` gesture for the operator on macOS; it never auto-applies it, and the exclusion is never written to a committed file.

**3. The trade-off is stated honestly, not hidden.** On macOS, pkit's own filesystem and egress are **not OS-confined** — they rely on the permission hook (intent) for their bound, not on Seatbelt (confinement). **All other bash remains OS-confined.** This is the residual gap COR-028's honesty discipline requires the realizer to declare: on macOS the confinement axis does not cover the one command that is excluded, and `sandbox status` / `probe` must report it as such ("N commands run outside the box," per ADR-008 rule 4).

**4. Follow-up — prefer a version floor over the exclusion if a fixed `uv` ships.** The exclusion is the correct end-state *given uv 0.9.8*. If a `uv` release newer than 0.9.8 fixes or avoids the SystemConfiguration probe under Seatbelt, then "require `uv ≥ X`" supersedes the exclusion as the cleaner end-state — confinement would once again cover pkit's own runtime, closing the residual gap rather than declaring it. This is a tracked follow-up, not a present capability.

## Rationale

**Why support macOS rather than declare it unsupported.** macOS is a first-class developer platform for the near-term adopters; declaring autonomy macOS-unsupported would forfeit the bulk of real use to avoid a single excluded command. The two-part mechanism keeps the *enforcement* half (the hook, intent-axis, the part that gates every tool call) fully working in-box, and isolates the loss to the *confinement* half of exactly one command. The honest residual-gap declaration (decision point 3) is precisely COR-028's prescribed response to a harness that cannot enforce a dimension — report the gap, do not drop the intent.

**Why the hook must be zero-dep `python3`, not `uv run --script`.** The hook runs per-tool-call inside the Seatbelt box. A `uv run --script` shebang means every gated call would invoke `uv`, which panics under Seatbelt (evidence 3) — enforcement would fail-open on every call, the worst outcome for the safety-critical layer. The system `python3` is present in the box and needs no network or cache, so the hook runs there cleanly. The stdlib YAML-subset fallback in the shared loader is what lets the same `decide()` core run without `ruamel.yaml`; routing it through the *shared* loader (not a hook-local copy) is what keeps ADR-003's one-`decide()` invariant mechanical rather than aspirational.

**Why exclude the CLI rather than accommodate it.** ADR-008's `narrowing` accommodation worked for the cache (evidence 2) but is *necessary-but-insufficient* on macOS: past the cache, `uv` hits the fixed `SCDynamicStore` denial that no `allowWrite`/socket/env accommodation can satisfy (evidence 3–5). `excludedCommands` is the only built-in escape Claude Code offers, and it widens. Widening it is, so it rides ADR-008's widening path exactly: loud, named-not-silent, never committed, always reported. Excluding *only* the one command that cannot run confined — while every other bash stays confined — is the minimal widening that restores autonomy.

**Why the exclusion is honest and not a hidden hole.** ADR-004 rule 4 and ADR-008 rule 4 forbid a believed-but-absent boundary. The exclusion does not pretend the CLI is confined; it declares the opposite and surfaces it on `status`/`probe`. The CLI is still *intent*-gated by the hook, so "unconfined" means "OS box does not bound its filesystem/egress," not "ungated." That distinction is the whole point of ADR-004's two-axis model: losing the confinement axis for one command does not lose the intent axis for it.

### Alternatives considered

- **Declare macOS autonomy unsupported.** Rejected — forfeits the primary developer platform over a single excludable command while the enforcement (intent) layer works fine in-box. The honest residual-gap declaration is strictly more useful than a blanket "unsupported."
- **Keep the `uv run --script` hook and accept fail-open on macOS.** Rejected — the hook is the safety-critical enforcement layer; making it panic-then-fail-open on every gated call under Seatbelt is the worst place to lose enforcement. A zero-dep `python3` hook keeps enforcement live in-box.
- **Accommodate `uv` further (more `allowWrite`, sockets, env levers).** Rejected on evidence — the `SCDynamicStore` mach-service denial is fixed in Claude Code's Seatbelt profile and unaffected by `UV_OFFLINE` / `ALL_PROXY` / `NO_PROXY` (evidence 4–5). Accommodation cannot reach past it; only exclusion (or a fixed `uv`) can.
- **Auto-apply the exclusion in `setup autonomy`.** Rejected — `excludedCommands` widens the boundary, and ADR-008 rule 4 / ADR-004 rule 4 forbid silently applying a widening allowance. `setup autonomy` names the gesture; the operator runs it.
- **Pin "require `uv ≥ X`" now instead of excluding.** Deferred, not taken — uv 0.9.8 is the current floor and panics; no fixed release is known to exist yet. The version-floor supersession is recorded as the preferred end-state (decision point 4) for when one ships, but the exclusion is what makes macOS autonomy work today.

## Implications

- **ADR-004 is amended in place (platform caveat), not superseded.** Its "genuinely native" confinement claim is qualified: confinement is platform-conditional, and on macOS with a uv-shim runtime the OS box cannot host pkit's own runtime, so the CLI is excluded and autonomy relies on the hook for that command. See the amendment in ADR-004's Implications.
- **ADR-008 is amended in place (premise correction), not superseded.** Its "runs fine once accommodated" premise is corrected: cache-accommodation is necessary-but-insufficient on macOS; `uv` then hits the fixed SystemConfiguration panic. Auto-accommodating the uv cache (#22) helps only where `uv` can run confined (Linux/bubblewrap), not macOS. See the amendment in ADR-008's Implications.
- **The hook shebang change and the loader fallback are implementation work (#21), not this ADR.** Dropping the `uv run --script` shebang on `.pkit/adapters/claude-code/permission-hook.py`, adding the stdlib YAML-subset fallback in `.pkit/permissions/`, and confirming the same-code invariant via the conformance fixtures land in the implementation issue. This ADR records only the decision.
- **The `failIfUnavailable` side-finding feeds #21.** `pkit permissions sandbox enable` must assert `failIfUnavailable: true` so the box never silently runs unconfined — the fail-closed-on-confinement invariant of ADR-004 rule 4 applied to the macOS reality. Tracked in the implementation arc, not enacted here.
- **The exclusion is reported, never committed.** `sandbox exclude` for the `pkit`/`uv` command rides ADR-008's widening path: per-invocation banner, never written to a committed file, never proposed by `detect`, never applied by `setup autonomy`, always counted by `sandbox status` / `probe`.
- **Cross-platform.** This stance is macOS-specific because the `SCDynamicStore` denial is Seatbelt-specific. On Linux/WSL2 (bubblewrap) `uv` can run confined once its cache is accommodated (ADR-008's `narrowing` path), so no exclusion is needed there and confinement covers pkit's own runtime. The platform-conditional split is the honest cross-platform picture.
- **No version bump.** This is a decision record; the observable behaviour change lands in the implementation issues (#21 / #22 / the exclude work), so `.pkit/VERSION` is unchanged per PRJ-002.
