---
id: PRJ-006
title: Opt-in permission-prompt diagnostic loop
status: accepted
date: 2026-06-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Under autonomy, confirmation prompts still recur project by project, and the operator has no systematic way to see *which* prompts recur, *why*, or *what would stop them*. The friction persists because prompt-reduction is half a feedback loop: the remediation step happens ad hoc, per incident, while the **capture → classify → measure** spine that would target it does not exist. Without that spine there is no ranking of what to fix and no proof a fix worked.

The signal is already produced where prompts originate. The permission hook is the per-call chokepoint (PreToolUse, every tool call), and the pure decision core returns a decision on every call. The methodology's permission model — its realizer ownership and fail-open contract (ADR-002), its same-code neutral core and catalog-as-data (ADR-003), and its intent×confinement axes with the "the allowlist is not a security boundary" stance (ADR-004), all under the model-realization decision (COR-028) — is the substrate this feature observes; it does not change it. A narrow precedent already exists: the `fewer-permission-prompts` skill scans transcripts to propose an allowlist for one group of prompts.

This is project-kit-the-project's tooling policy, so it is a PRJ — the same class as the version-bump policy (PRJ-002), not a methodology principle (COR) and not a new architectural decision. The architectural custodian reviewed it and judged it changes no permission-model ownership tier, so it is not a new ADR. The one architectural boundary it touches — whether a fix may write the permission catalog — is pinned here on paper and folds into the foundational ADRs only if the deferred auto-fix arc is ever built.

## Decision

**project-kit adds an opt-in permission-prompt diagnostic loop to the permissions surface; its first shipped form (MVP) captures prompts, classifies them, and reports remediations it *recommends* rather than applies.** Unattended auto-fix is deferred. The loop is surfaced as `pkit permissions diagnose on | off | status | report`.

Six sub-decisions fix the shape:

1. **Opt-in, off by default.** Diagnosis runs only inside a bounded "diagnostic session." While off (the default), the hook performs one cheap check per call and logs nothing. While on, it appends each prompted/deferred decision to a local log. Rationale: per-call cost, log noise, and command-argument privacy all argue against always-on capture.

2. **Capture lives in the adapter, not the core.** The "prompt" is a harness behaviour, so capture is written in the Claude-Code adapter hook *after* the decision is computed, gated on the deferred verdict, and wrapped so a capture failure can never change a decision or break fail-open. The shared decision core stays pure (it is the same code the CLI runs). The classifier, taxonomy, and report stay harness-agnostic in the permissions surface. Because the hook observes only its own deferral — not whether the harness ultimately prompted — the captured signal is a *superset* of real prompts; the report states **coverage**, not a predicted prompt-count decrement.

3. **Classification is advisory; a safe-set gates any fix.** The group classifier orders and explains the report, but it never authorizes a change. A curated read-only/safe-command set — not the classifier — is the gate for any auto-applied fix, so a misclassification can never widen the wrong thing.

4. **The auto-fix bright line (resolved on paper now).** If and when the auto-fix arc is built, a fix may auto-apply **only a grant of a privilege already in the permission catalog**, through the existing grant + settings-merge path. **Authoring a new catalog privilege is never auto-fixable** — it is always a proposed operator task. The catalog is the operator-owned trust vocabulary and the source of the guardrail deny set; an agent minting privileges erodes the operator's *intent* declaration (it does not breach a security boundary — per ADR-004 the allowlist is not one — but intent erosion is the harm). Egress remediation is likewise recommend-only: accommodation is keyed on detected toolkits, not on a host observed in a prompt, and auto-opening egress from observed traffic is precisely the anti-pattern ADR-004 warns against.

5. **MVP cadence and guards.** Cadence is on-demand `report` only; a session-end auto-summary and any scheduled routine are deferred. A diagnostic session auto-expires (the armed marker carries a TTL) so it cannot stay silently on, and the log is size-capped (drop-oldest). Command-tail redaction is on by default and the log is git-ignored through the pkit-owned `.pkit/.gitignore` render (its path is contributed to the aggregated `runtime_ignore` set and rendered wholesale, per ADR-009 Amendment 1) — both land in the same change as capture, not later.

6. **Defer the generic framework (per COR-007).** Permission-prompts is the first and only diagnostic probe today. The capture→sink→report seam is factored but kept in place; a generic `diagnostics` home is extracted only when a second probe (e.g. sandbox faults, egress denials, command timing) actually recurs. Until then the home stays `pkit permissions diagnose`. The group taxonomy itself lives in code and docs, not in this record — it is inventory that will churn as the classifier meets real data.

The full design space, the worked report shape, and the critic/architect review outcomes are in the source scratchpad (`.pkit/scratchpad/active/2026-06-19-permissions-diagnose-prompt-loop.md`).

## Rationale

**Why opt-in over always-on.** The hook fires on every tool call; always-on capture is real per-call overhead and a standing privacy surface (raw commands carry tokens and paths). A diagnostic is something you reach for while actively reducing prompts, then put down — a bounded session matches that use and keeps the default path free.

**Why capture in the adapter and not the core.** The decision core is shared by the hook and the CLI and must decide identically; persisting a side-effect inside it would both break that same-code property and put I/O in a function whose whole value is being a pure decision. "A prompt happened" is only observable at the harness boundary anyway, so the adapter is the only honest capture point.

**Why advisory classification with a safe-set gate.** The hook's deferral reason carries no group signal, so the classifier must infer groups from raw command text — inherently brittle. Making the classifier advisory-for-ranking and gating fixes on an explicit safe-set means the dangerous case (a misclassified item in the auto-fixable band) cannot occur: the worst outcome of a misclassification is a wrong count, never a wrong grant.

**Why the catalog bright line.** The realizer grants *named catalog privileges*; it cannot add raw command patterns. So an auto-fix for an un-cataloged command would have to author a new catalog privilege unattended — writing the file that also defines the guardrail deny set. That is operator-owned territory. Recording the line now (rather than when the auto-fix arc is built) follows the project's established "resolve the footgun on paper before someone re-introduces it" practice.

**Why defer the framework.** With exactly one probe, a generic probe interface would be guessed at, not validated — the speculative-generality trap. The same extract-on-the-second-instance discipline was just applied to the demo-recording capability's format/recording split; this is the same call.

**Why PRJ.** The decision is project-kit-specific tooling policy — how this project observes and reduces its own prompt friction — not a universally-applicable methodology principle and not an architectural boundary change. That places it with PRJ-002, not in COR or ADR.

## Implications

- **Versioning.** Shipping the MVP adds a new CLI command surface (`pkit permissions diagnose …`), so it is a surface change and bumps `.pkit/VERSION` per PRJ-002. It is a pure addition (new opt-in command, new capture call in an already-realizer-owned file, new neutral classifier) and breaks nothing installed, so it needs no COR-010 migration. Confirm with `pkit migrations check-diff` at commit time regardless.
- **Where the code lands.** Capture in the Claude-Code adapter hook; the diagnostic-session state and the log under the permissions area; the classifier/report in the harness-agnostic permissions surface; the decision core untouched.
- **Privacy footprint.** The diagnostic log is a new local artifact carrying redacted command strings; it is git-ignored via the pkit-owned `.pkit/.gitignore` render (per ADR-009 Amendment 1) and size-capped. The redaction-on-by-default and ignore must ship with capture, not after.
- **The deferred auto-fix arc.** Building unattended `--fix` reopens two questions this record leaves closed-by-deferral: a host→toolkit map for egress, and any path that would author catalog privileges. The moment such a path is proposed, it escalates to the architectural custodian and folds the catalog bright line into the realizer-ownership / intent-confinement ADRs (ADR-002, ADR-004); until then this record carries it.
- **Relationship to `fewer-permission-prompts`.** That skill remains the transcript-side cross-check (transcripts can corroborate "was actually prompted," which the hook over-counts); it is not folded into this feature in the MVP.
- **The slices and the group taxonomy** are implementation inventory and live in the source scratchpad and the eventual issue arc, not in this record.
