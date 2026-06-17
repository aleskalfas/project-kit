---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-17
---

# Harness metadata protection scoping

> Follow-up parked by ADR-017. The finding is recorded and accepted; this note tracks the **upstream harness fix pkit cannot file itself**, plus the broader question of how pkit should relate to harness-built-in denies. Process later.

## The finding (ADR-017, accepted)

A confinement-toolkit allowance is **additive within what the harness permits; it cannot override a harness-built-in deny.** Measured by a fresh-session spike (canary-proven fresh): with `node_modules` in the active `allowWrite`, writes to `.idea` and nested `.git` *inside* `node_modules` were still **DENIED**. The harness's bare-name `.git`/`.idea` protection sits above `allowWrite` and wins.

**Measured deny surface (reference):**
| Path | Under the box |
|---|---|
| `.idea` (anywhere, incl. inside `node_modules`) | DENIED |
| nested `.git` internals inside `node_modules` | DENIED |
| `.git` at the real repo root | ALLOWED (git ops need it) |
| `node_modules` itself (plain writes) | ALLOWED (workspace) |
| planted git hook inside `node_modules` | did NOT execute |

## Upstream follow-up (pkit can't file it)

The real fix is **harness-side**: Claude Code should scope its `.git`/`.idea` protection to the **authored repo root** and stop policing the contents of downloaded `node_modules`. The protection is right for the developer's own repo metadata; it over-fires on vendored junk inside third-party packages (a transitive dep, `iconv-lite@0.6.3`, ships a stray `.idea/`, EPERMing `pnpm install` under the box).

**Action to process later:** file this with the Claude Code / Anthropic harness team when there's a channel. When it lands, the interim workaround (below) retires — the ADR-014-style "harness-fix-preferred over the present mechanism" structure.

## Interim adopter workaround (in effect now)

`sandbox exclude <package-manager>` — run *install* unconfined (the ADR-008 rule-4 widening gesture: loud, never-auto, never-committed, always-reported) while ongoing agent work stays boxed. Honest cost: install (the riskiest op — runs third-party postinstall scripts) runs outside the box under this workaround; acceptable only as a temporary, explicit operator gesture. A project-local `.pnpm-store` is writable by default (no grant needed).

## Broader question (the reason this is a note, not just a ticket)

How should pkit relate to **harness-built-in denies** generally — protections the harness enforces that pkit's confinement model can neither see nor override?
- Should pkit **detect and surface** them (a "harness deny surface" report in `permissions overview` / `sandbox status`), so an adopter knows what the box protects *beyond* pkit's model and doesn't reach for a toolkit `allow-write` that can't lift them?
- `permission-enforcement.yaml` already declares which dimensions the harness realizes; should it also declare harness denies pkit can't reach, so `permissions diff` can label "this is a harness floor you can't reconfigure"?
- This is the COR-028 honesty discipline applied to the *floor* the harness imposes, not just the model pkit declares.

## Related records

- ADR-017 (the finding; this note's parent).
- ADR-014 (harness limitation shapes confinement; exclusion-now / harness-fix-preferred structure — same shape).
- ADR-008 / ADR-015 (the confinement-toolkit model ADR-017 bounds).
- Originating consumer note: `trip-planner-agent-app/.pkit/scratchpad/active/2026-06-17-node-toolchain-confinement.md` (its `allow-write`-override recommendation is **corrected** by ADR-017 — that note should be updated to record the assumption as disproven).
