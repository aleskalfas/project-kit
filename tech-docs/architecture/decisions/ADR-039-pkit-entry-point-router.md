---
id: ADR-039
title: Fold the router shim into a CWD- and pin-aware pkit entry point
status: accepted
date: 2026-07-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the installed `pkit` binary becomes aware of both *where it is
run* and *what version the project pins*, and picks one of three routes cheaply —
before any heavy import — on every invocation. (1) Inside a project-kit source
checkout it execs that checkout's in-tree dispatcher (`.pkit/cli/pkit`), so the
working tree runs and the deploy-primitive bypass survives. (2) When the project
pins a version different from the running binary, it re-execs `uvx
project-kit@<pin>`. (3) Otherwise it runs itself. This folds the logic of today's
separate `pkit-router` shim into the tool, so adopters and developers share **one**
install. It is only sound because [ADR-033](ADR-033-official-install-bundles-content.md)
version-locks bundled content to the binary: re-execing to `@<pin>` brings CLI code
and methodology content from the *same* wheel, so they cannot diverge. An
unresolvable pin degrades loudly to running self — it never hard-fails mid-command.

## Context

Two `pkit` entry points coexist today. The installed binary
([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md), `uv
tool install git+…`) runs a single global release. Alongside it, a hand-installed
shim — `scripts/pkit-router`, placed on PATH ahead of the binary via `mise run
pkit:router-install` — makes `pkit` CWD-aware: inside a project-kit source checkout
it delegates to that checkout's in-tree dispatcher (`.pkit/cli/pkit`,
[PRJ-001](../../../.pkit/decisions/project/PRJ-001-cli-binary-name.md)), which runs
the working tree under `uv run --project <checkout>` and preserves the
deploy-skills / merge-settings adapter-primitive bypass; anywhere else it falls
through to the pinned global release. A developer juggling several source checkouts
plus adopter repos needs that routing; an adopter with a single install does not
have it.

Two gaps motivate this decision. First, the router is a *second thing to install*
and maintain — a versioned snapshot on PATH that nags to reinstall when a checkout
ships a newer `ROUTER_VERSION`. Adopters who never touch a checkout still carry the
conceptual overhead of "which pkit am I running". Second, the router routes by
*checkout presence* only; it has no notion of a project **pinning a specific
released version**. With ADR-033 landed — the official install now bundles
version-locked methodology content — a project can meaningfully pin "run me under
project-kit vX.Y.Z", and nothing today honours that pin.

Issue #463 works the resolver design; #464 (disciplined release tagging) and #465
(the implementation + retirement) are its siblings. The critic and architect
reviewers ran on the design across the release-and-versioning discussion that
produced it.

## Decision

**The `pkit` entry point becomes CWD- and pin-aware, folding the `pkit-router`
shim's routing into the installed tool, so there is one install for adopters and
developers alike.** On every invocation it selects one of three routes,
**cheap-first** — the route is chosen *before* the heavy import, so the fast path
never pays Python cold-start it can avoid:

1. **Source checkout → exec the in-tree dispatcher.** When the invocation resolves
   inside a project-kit source checkout, exec that checkout's `.pkit/cli/pkit`,
   running the working tree. This preserves the deploy-primitive bypass the shim's
   route delivers today.

2. **Project pins a version ≠ me → re-exec `uvx project-kit@<pin>`.** When the
   enclosing project pins a version that differs from the running binary's,
   re-exec `uvx project-kit@<pin>` and let that process serve the command.

3. **Match, or no pin → run self.** When the pin matches the running binary, or the
   project pins nothing, run in-process.

**D1 — Version-lock soundness rests on ADR-033.** Re-execing to `uvx
project-kit@<pin>` brings CLI code *and* bundled content *from the same wheel*:
`find_source_kit()` keys off the installed package location
([ADR-033](ADR-033-official-install-bundles-content.md)), so the re-exec'd process
falls through to that pin's bundled `_kit/`. Code-at-pin and content-at-pin cannot
diverge. This resolver is only possible *because* ADR-033 collapsed the
binary-vs-content drift axis; without it, re-execing the code to a pin would say
nothing about the content that pin syncs.

**D2 — Graceful degradation is mandatory.** An unresolvable pin — offline, an
untagged version, missing auth — falls back to running self with a **loud drift
warning**. The resolver never hard-fails mid-command over a pin it cannot fetch; a
degraded-but-running command beats a broken one.

**D3 — Pin correspondence assumes disciplined tagging.** `uvx
project-kit@vX.Y.Z` resolves the git tag `vX.Y.Z`, so route 2 assumes total
tag⟺`.pkit/VERSION` correspondence. That correspondence is a release-discipline
property, owned by #464 (and already mandated in spirit by PRJ-004, which cuts
annotated tags matching `.pkit/VERSION`). The resolver depends on it; it does not
enforce it.

The **pin source** — whether the project's pin is read from `.pkit/VERSION` or from
a dedicated pin file — is left to the implementation (#465) to decide and reconcile
with ADR-033, not fixed here.

## Rationale

**Why fold the shim in rather than keep two installs.** The router shim is a
maintained snapshot on PATH with its own version and reinstall nag; it exists only
because the entry point could not route itself. Folding its logic into the tool
removes the second install, the reinstall ceremony, and the "which pkit"
ambiguity — one binary does the right thing by CWD and pin. The shim's one genuine
capability worth preserving — the source-checkout bypass — becomes route 1, so
nothing is lost.

**Why route before the heavy import.** Routing is a decision about *which* process
should serve the command; making it after paying Python cold-start would tax every
fast-path invocation (route 3 match, route 1 checkout exec) for a cost only route
2's minority pays. Cheap-first keeps the common case cheap.

**Why the accepted tradeoff is worth recording honestly.** Route 2's `uvx
project-kit@<pin>` reintroduces **on-demand fetch/build at command time** —
precisely the hazard ADR-033 rejected for *upgrade* time. It is bounded and cached
per version, but real on first use of a pin. This is a deliberate, eyes-open
tradeoff: the alternative (no pin honouring) leaves ADR-033's version-lock
guarantee unusable at the entry point. The near-term mitigation is **prebuilt
artifacts (#359)**, which turn build→pull; that work is elevated in priority by
this decision (it is no longer independently deferrable).

**Why graceful degradation, not a hard fail.** A pin that cannot resolve
mid-command — a laptop offline, a tag not yet pushed, an auth gap in CI — must not
brick `pkit`. Running self with a loud warning surfaces the drift without stranding
the operator. A hard fail would make the resolver *more* fragile than the
single-binary status quo it replaces.

### Alternatives considered

- **Keep the `pkit-router` shim as a separate PATH install.** Rejected — it is a
  second thing to install, version, and reinstall-nag, and it cannot honour a
  project's version pin (it routes by checkout presence only). Folding removes the
  install and adds pin-awareness.
- **Honour pins by re-execing only the CLI code, not the whole wheel.** Rejected —
  it re-introduces the binary-vs-content drift axis ADR-033 exists to collapse;
  code-at-pin with content-at-head is exactly the mismatch that wedges an adopter.
- **Do the fetch/build eagerly (pre-warm every pin).** Rejected — pays the build
  cost the tradeoff bounds to first-use, for pins that may never be exercised.
  Per-version caching plus prebuilt artifacts (#359) is the right cost curve.
- **Hard-fail on an unresolvable pin.** Rejected — makes the resolver more fragile
  than the single binary it replaces; a loud degrade preserves availability.

## Implications

- **Retire `scripts/pkit-router` and `mise run pkit:router-install`.** The shim and
  its install task go away once the entry point routes itself; the "install the
  router" step leaves the developer setup docs.
- **The retirement ships a migration with the implementation (#465).** Removing
  `scripts/pkit-router` and changing the install procedure is a rename/removal in a
  kit-owned tree and a breaking install-procedure change — a surface change that
  must ship a migration in the same change-set
  ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md),
  `rules/core.md` rule 7). The migration is idempotent and instructs installed
  router copies to uninstall.
- **The pin source is an implementation call (#465).** Whether the project pin
  reuses `.pkit/VERSION` or a dedicated pin file is decided in implementation and
  reconciled with ADR-033's resolution model; this record fixes the routing, not
  the pin's storage.
- **Prebuilt artifacts (#359) are elevated, not independently deferrable.** By
  reintroducing command-time fetch/build on route 2, this decision makes #359 the
  near-term mitigation that turns build→pull. Its priority is now coupled to this
  resolver's rollout.
- **Depends on disciplined release tagging (#464).** Route 2's `uvx
  project-kit@vX.Y.Z` → tag `vX.Y.Z` resolution assumes total
  tag⟺`.pkit/VERSION` correspondence; #464 owns that discipline, PRJ-004 already
  mandates matching annotated tags.
- **Stands on** ADR-033 (version-locked bundled content — the soundness
  precondition), PRJ-004 (`uvx`/git-URL distribution and tag-matches-VERSION),
  PRJ-001 (the `pkit` dispatcher route 1 execs), and COR-010 (the migration
  obligation on the retirement). Establishes the entry-point router; supersedes
  nothing — no prior router ADR exists.
