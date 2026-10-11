---
id: ADR-044
title: pkit upgrade detects a stale tool and instructs; it does not self-install
status: accepted
date: 2026-08-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

`pkit upgrade` refreshes a project's `.pkit/` **from the installed tool's bundled kit** — it cannot update the *tool* itself, and today it can't even tell you the tool is behind: an adopter on a stale tool sees *"nothing to upgrade"* and has no idea the fix lives in a different command (`uv`). This ADR makes `pkit upgrade` **detect** a newer released tool and **print the exact command** to update it. It deliberately does **not** run `uv tool install` itself in this increment: auto-installing would replace the global binary every project on the machine shares, the confinement sandbox would gate that with its own prompt regardless (so the "seamless" auto-run saves a sandboxed operator nothing), and the genuinely seamless end-state — **option D** (deferred): a per-project pin the router serves via `uvx`, with no global mutation at all — retires the auto-install path rather than building on it. Detect-and-instruct is the smallest change that kills the actual confusion, ships safely, and commits us to nothing the seamless design would undo.

## Context

Two distinct upgrades exist, done by two tools. The **tool** (the `uv`-installed wheel and its bundled `_kit` snapshot, [ADR-033](ADR-033-official-install-bundles-content.md)) is shared across *all* the user's projects; **`pkit upgrade`** ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)) brings *one* project's `.pkit/` up to whatever that tool bundles. `pkit upgrade` reads the bundle and is fully **offline**; it has no path to update the tool or discover a newer release. The [ADR-039](ADR-039-pkit-entry-point-router.md) router already re-execs a *pinned* version of pkit via `uvx project-kit@<pin>` from a compiled-in distribution URL — so the fetch-a-released-version machinery exists — but nothing discovers "the latest," and the router's pin route is inert for adopters (they carry no `.pkit/VERSION` — it is not in the propagated install set, a fact surfaced during the #545 provenance work). The live failure: an adopter (AUJ) ran `pkit upgrade` against a tool bundling an older backbone, got *"Already at backbone vX; nothing to upgrade"*, and the remedy — a manual `uv tool install --force …@vY` — was neither run nor named.

A prior "fold the `uv tool install` into `pkit upgrade`" design was reviewed and **rejected**: its "pinned project → raise the pin" branch is inert (no adopter pin file exists), collapsing it to *always replace the global tool*; and replacing a shared binary as a silent side effect of a per-project command is a consent/blast-radius regression the sandbox would prompt on anyway. This ADR records the converged, narrower outcome.

## Decision

**`pkit upgrade` detects a newer released tool and instructs; it does not install it.**

- **D1 — Detect, best-effort, offline-safe.** `pkit upgrade` queries the release source (a `git ls-remote --tags` against the compiled-in distribution URL, the same URL the router already uses) for the latest tag. If the source is unreachable (offline, no credentials), it **degrades loudly and continues** with today's behaviour — sync the project from the current bundle — and never fails the command on the check. The network call is best-effort, not a gate.
- **D2 — Instruct, don't install.** When the running tool is behind the latest release, `pkit upgrade` prints the **exact command** to update the tool (`uv tool install --force <url>@v<latest>`, then re-run `pkit upgrade`) and *why*. It runs nothing itself. When the tool is current, it says so plainly instead of the ambiguous "nothing to upgrade."
- **D3 — uv-only, and scoped to a normal adopter install.** The instruction assumes a `uv`-tool install (per the uv-only distribution narrowing, PRJ-004). It is **suppressed on a source checkout / self-host** (where reinstalling a released tag over working-tree code would be nonsensical — the router's route-1 / the upgrade self-host short-circuit already identify these). Because the increment only *prints a string*, a mis-detected context degrades to a suboptimal message, never a destructive action.
- **D4 — Boundary: the tool, from its distribution URL.** Self-update concerns the **tool** (repointed from the compiled distribution URL); it never touches externally-sourced *content* ([COR-041](../../../.pkit/decisions/core/COR-041-external-source-distribution.md)). An install whose real upstream diverges from the compiled URL (a fork building its own wheel gets its own URL and is fine; a diverging source is not) is out of scope for the printed instruction's correctness — print-only sidesteps the "install from the wrong upstream" hazard entirely, which an auto-run would not.

### Deferred (named, not built)

- **The consented auto-run** (`pkit upgrade` offers `[y/N]` then runs `uv tool install`): sound if ever wanted, but it saves a sandboxed operator nothing (the sandbox gates the global install regardless) and is retired by option D. If built, it must use a **dedicated `PKIT_SELF_UPDATED` interlock** (not the router's `PKIT_ROUTED` bypass — different loop, different scope), terminate the self-update step **regardless of version comparison** (else an install-succeeds-but-version-skews infinite loop), hard-abort on any non-zero `uv tool install` exit (a botched force-install can brick the shared binary), and **honor the sandbox's own gate — never allowlist `uv tool install --force` to suppress it** (core rules 14-15).
- **Option D — the per-project pin the router serves via `uvx`.** The actual seamless end-state (no global mutation, per-project scope, reproducible). Needs a pin-file ownership design under the no-shared-files invariant + an ADR-039 refinement. The next increment.

## Rationale

**Why instruct, not install (in this increment).** The friction that surfaced is *confusion* — "nothing happened, what do I run?" A printed command kills that completely, ships now, and adds no new mutation, no self-replace, no cross-project blast radius, no upstream-source hazard. The auto-run's only benefit over a printed command is saving one paste — and for the careful/sandboxed operator it saves even that nothing, because the sandbox prompts on the global install anyway. Investing in the auto-run's machinery (the interlock, install-detection, partial-failure handling) would build a global-mutation path that option D deletes — the wrong side of [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)'s "don't build the heavier abstraction a successor removes."

**Why it layers above the router, leaving ADR-039 closed.** Self-update is a new upgrade-time behaviour that *calls* the router's fetch machinery (the compiled distribution URL, the `uvx` pattern) without changing the router's three-route / two-guard decision. The deferred auto-run's `PKIT_SELF_UPDATED` interlock is owned by the upgrade path, not the router — a distinct loop from route re-selection. So ADR-039 is unchanged; this composes on top.

**Why the two-prompt posture is right (for the deferred auto-run).** pkit's `[y/N]` discloses *intent and blast radius* ("this replaces the shared tool for all your projects"), which the sandbox cannot articulate; the sandbox prompt authorises the *mechanism* (network egress + global write). They gate different things at different layers. Collapsing them requires defeating a layer — the exact rule-14/15 violation. Two prompts for a global-binary replacement is honest, not a defect to engineer away.

### Alternatives considered

- **Fold a silent `uv tool install` into `pkit upgrade` (auto-run, no prompt).** Rejected: inert pin branch → always-replace-the-global-tool, silent cross-project blast radius, sandbox prompts anyway.
- **Consented auto-run (`[y/N]` then run) as v1.** Rejected *for this increment* (deferred, not killed): saves a sandboxed operator nothing; option D retires the global-mutation path it builds.
- **A separate `pkit self-update` command.** Deferred: worth revisiting only if demand for a command-driven tool update appears after D; a per-project command touching the global tool is the scope tension D dissolves.
- **Do nothing (leave "nothing to upgrade").** Rejected: it is the confusing message that motivated this.

## Implications

- **`pkit upgrade`** gains a best-effort `git ls-remote --tags` staleness check against the compiled distribution URL, an offline-degrade path (warn + proceed with today's sync), a "your tool is behind — run: …" instruction when stale, and a clear "tool is current" message when not. Suppressed on source-checkout / self-host.
- **No new mutation, no network gate.** The check never fails the command; the command never installs anything. The permission/sandbox surface is unchanged (no `uv tool install` is issued by pkit in this increment).
- **Depends on the uv-only narrowing** (PRJ-004 + PRJ-003 amended): the printed instruction is a `uv` command.
- **Surface change → a backbone version bump** (a new observable `pkit upgrade` behaviour), declared via a changeset. Migration-free (additive; no state to bridge).
- **Stands on** ADR-033, ADR-039, COR-007, COR-010, COR-041, PRJ-004 — all accepted (PRJ-004 amended alongside). ADR-039 is not reopened.
- **Next increments, in order:** option D (per-project pin + ADR-039 refinement) is the seamless end-state; the consented auto-run is only worth building if D proves insufficient.

## Amendment (2026-08-10)

**`pkit upgrade` now ACTS on a stale tool, not just instructs — it self-updates the global binary and re-execs.** This turns the decision's detect-and-**instruct** into detect-and-**act** (the "consented auto-run" the Implications named as a later increment). Status is unchanged (`accepted`); D1 degrade, D3 source-checkout suppression, and the best-effort/never-fail posture all stand — the amendment adds an action ahead of the instruct, with instruct as the fallback.

**What changed.** When the running tool is behind the latest release and self-update is allowed, `pkit upgrade` runs `uv tool install --force <dist>@v<latest>` and then **re-execs the same command under the freshly-installed version** (guarded by `PKIT_SELF_UPDATED` against a re-exec loop) so the content sync + pin run under the new bundle — one seamless command. It **degrades to the original instruct** (print the exact command) when: the session is **non-interactive** (no TTY — so a network install is never forced under automation/CI), `--no-self-update` is passed, or the install **fails or is declined** (the sandbox gates a global-binary mutation; a decline surfaces as a non-zero exit and degrades, never bricks). Run **outside any project**, `pkit upgrade` performs the tool self-update alone (via `run_tool_update`) instead of erroring on a missing project/manifest — the "just update my tool" case.

**Why now — the blast-radius objection dissolved.** The original decision withheld the auto-run because reinstalling the shared global binary moved **every un-pinned project at once** (cross-project blast radius the sandbox gates anyway). **Pin-by-default (ADR-049, amended; shipped v1.145.0)** insulates projects from the global tool — a pinned project runs its own version via the ADR-039 router's `uvx` re-exec and does not follow the global binary. So updating the tool no longer disturbs pinned projects, and the reason to withhold the action is gone. The named precondition ("only worth building if D proves insufficient / once D exists") is met: D shipped, and this completes the seamless end-state D pointed at.

**Invariant preserved.** Self-update fires only on the **un-pinned / non-routed-child** path (the existing staleness-check site, suppressed under the router bypass). A pinned project's `pkit upgrade` still advances its own pin via `uvx` and never touches the global tool — the ADR-039 multi-version-coexistence invariant (a project on an older pin runs that older version) is untouched.

**Rollout / migration.** The behaviour lives in the upgrading code, so existing adopters get it on their next `pkit upgrade` under a version that carries it; `--no-self-update` preserves the old print-only behaviour. Migration-free (additive behaviour; no state to bridge). The permission surface *does* change — `pkit upgrade` may now issue `uv tool install` — but only interactively and with a clean degrade, consistent with the sandbox's gating of global-binary mutations.
