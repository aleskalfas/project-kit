---
id: COR-039
title: Capabilities declare dependencies on external system tools
status: proposed
date: 2026-06-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A capability (COR-017) often needs a tool that lives **outside** the kit entirely — a separately-installed binary, daemon, or runtime: a screen-recorder, a browser engine, a compiler, a container runtime. COR-030 lets a capability declare a versioned dependency on *another capability*, and COR-017's `requires_backbone` constrains the backbone — but neither covers a dependency on an external system tool. Today such a tool's absence is invisible to the lifecycle: a capability installs cleanly and then fails deep inside an operation when it reaches for a binary that isn't there, or one that is present but too old.

Two things make external-tool dependencies different from capability dependencies, so COR-030's disposition does not transfer unchanged:

- **Install and use are separated in place and time.** A capability can legitimately be *authored and installed* on a machine that cannot *run* its heavy operation — you draft a recording on a laptop without the recorder, then record on a workstation that has it. Refusing the install (COR-030's disposition for an absent capability dependency) would break that author-anywhere neutrality.
- **There is no kit-managed installer for an external tool, and its state can drift.** The kit can install a capability; it cannot install a recorder or a compiler. Detection, not provisioning, is all the lifecycle can offer — detection differs per operating system, and the tool can be upgraded, downgraded, or removed after install with no lifecycle event the kit ever sees.

## Decision

**A capability may declare dependencies on external system tools in its manifest; the kit warns about a missing or out-of-range tool at install time, and the capability's operation that uses the tool refuses to run when it is unsatisfied at use time.**

- **`requires_system`** — an optional field in the capability's `package.yaml` (beside `requires_backbone` and COR-030's `requires_capabilities`): a list of external tools, each carrying enough to *detect and diagnose* it — a name, a minimum version, a per-operating-system install hint, and a probe by which the kit tests presence and version. The capability schema owns the exact shape (COR-018); this record owns the rule that the declaration exists and what the kit and the capability do with it.
- **Install warns, never refuses.** When a dependent is installed while a declared tool is absent or out-of-range, the lifecycle emits a **loud, actionable warning** (install or upgrade the tool, with the per-OS hint) and proceeds. Authoring and installation stay possible on a machine that will never run the gated operation.
- **The use-time gate is the capability's obligation, and it is the real guarantee.** The capability's operation that invokes the tool **must refuse to run** when the tool is absent, out-of-range, or undetectable, with actionable remediation. As in COR-030, this runtime guard lives in the dependent, not in this mechanism: the kit contributes the declaration, the install-time warning, and the preflight, but it does not wrap a capability's operations — so the use-time refusal is owned by the capability. This record mandates that obligation for any declared tool; the install-time warning is only an early, friendly surface on top of it.
- **An undetectable tool is a gap, never a silent pass.** When the probe cannot establish presence or version (no version output, the tool off the lookup path, the probe itself erroring), the use-time gate treats the tool as **unsatisfied** (fail-closed) and the install path warns. The kit never lets an operation proceed on an indeterminate probe and then fail deep inside the run.
- **A preflight check verifies the declared set.** The kit offers an operator-invokable health check that reports, across the installed capabilities' declared tools, whether each is installed, in range, and reachable, with per-OS remediation for each gap — so an operator can confirm readiness before attempting the gated operation rather than discovering a gap mid-run.

**Deliberately out of scope** (consistent with COR-030): the kit never *installs* or *upgrades* an external tool, and never auto-resolves a gap — provisioning is the operator's job. A per-tool *install-blocking* disposition (letting a capability that is inert without a given tool opt into refuse-at-install rather than warn) is deferred until a consumer needs it; the uniform rule is warn-at-install for every declared tool.

## Rationale

- **Why warn-at-install but gate-at-use, rather than COR-030's refuse-at-install.** The disposition is keyed to whether the dependency is needed *to install* or only *to run*. A capability dependency is needed for the dependent to function at all, so an out-of-range one refuses early. An external tool is needed only by the specific operation that calls it; refusing the install would forbid the legitimate author-on-one-machine, run-on-another workflow for no *additional* safety gain over a loud warning, since the use-time gate already prevents a broken run.
- **Why the guarantee lives at use time.** No install-time check can prevent the tool from being absent or too old at the instant the operation invokes it — and because the tool lives outside the kit, its state can change after install (upgraded past the declared range, downgraded, or removed) with no lifecycle event the kit can observe. The install-time warning is therefore a point-in-time snapshot that can go stale silently; the use-time gate and the on-demand preflight are the only points the kit re-checks, so the durable guarantee can only be the capability refusing to run.
- **Why fail-closed on an indeterminate probe.** An external-tool probe is less reliable than a kit-owned manifest read: a tool may lack a parseable version, sit off the lookup path, or the probe may error. Treating "can't tell" as "unsatisfied" at use time keeps the failure at the friendly gate with remediation, rather than letting an ambiguous environment produce a deep mid-run failure.
- **Why a version range and a probe, not presence-only.** A present-but-too-old tool is a real failure — an interface or flag the capability relies on may be missing — so a minimum version converts that into a diagnosable gate rather than a silent runtime error. Because there is no kit-managed installer, the declaration must also carry *how to detect* the tool, since presence cannot be assumed from a canonical install path.
- **Why detection lives in the declaration, per operating system.** External tools install and present differently across platforms, so the install hint and probe are inherently per-OS. Folding that variation into the declared data keeps the per-OS detail as data rather than scattering it through capability code — in the same spirit as COR-027's preference for expressing variation as capability data.

### Alternatives considered

- **Refuse at install (reuse COR-030's disposition).** Rejected — breaks author-anywhere neutrality for no additional safety gain over a loud warning, since the use-time gate backstops a broken run.
- **Use-time gate only, no declaration.** Rejected — leaves the dependency invisible to the lifecycle and to a preflight check; an operator cannot see what a capability will need until it fails, and every capability re-implements ad-hoc detection.
- **Fold external tools into COR-030's `requires_capabilities`.** Rejected — a different subject (a tool outside the kit, not a capability) and a different disposition (warn-not-refuse at install, probe-based detection rather than a manifest read); conflating them would muddy COR-030's clean refuse-at-install rule.
- **Have the kit install the tool.** Rejected — there is no universal installer for arbitrary external tools, provisioning is the operator's responsibility, and auto-provisioning contradicts the methodology's consistent warn/refuse-with-hint disposition (COR-030).

## Implications

- A capability manifest gains an optional `requires_system` list. The capability schema carries the field's shape and bumps its `schema_version`; because the change alters an installed adopter's manifest contract, it ships with a migration in the same change-set (COR-010). Capabilities that declare none are unaffected.
- The lifecycle gains a warn-only external-tool check at install (distinct from COR-030's refuse-on-capability-dependency check); the kit gains an operator-invokable preflight that reports the declared set's state; and each capability with a declared tool gains a use-time gate it owns. Only COR-030's **version-range comparison** primitive transfers cleanly — the **detection** half is genuinely new (a per-OS probe whose result may be present, out-of-range, or indeterminate), not a read of a kit-owned manifest.
- A capability's use-time guard is owned by that capability and recorded in its own decisions; this record establishes the cross-capability contract (the declaration, the install warning, the preflight, and the obligation to gate at use), not any one capability's runtime check.
- This **stands on COR-017** (the capability primitive) and **COR-030** (the dependency-declaration pattern it parallels on a new axis), and **supersedes nothing**. COR-030 may gain a one-line forward pointer.
