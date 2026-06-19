---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-19
---

# An opt-in permission-prompt diagnostic loop

## The question

Autonomy under the active sandbox still produces confirmation prompts, project by project, and the operator has no systematic way to find out *which* prompts recur, *why*, and *what would stop them*. How do we turn "confirm fatigue" from a per-incident annoyance into a measurable, closable loop — and do it so the mechanism is **opt-in** (off by default) and **extensible** to future diagnostics without over-building today?

This note maps the design space. It is a brainstorm, not a decision — the eventual crystallisation is a permissions-capability feature plus a DEC.

## Why this is a loop, and what's missing

The reason prompt-fatigue persists is that the remediation half of a feedback loop exists while the measurement half does not:

```
capture every prompt → classify → group + rank → map group → remediation → apply → re-measure (group shrinks)
                    └──────────────── MISSING TODAY ────────────────┘        └─ ad-hoc, per-incident ─┘
```

Today only the right-hand side happens, reactively, when a human notices friction. Without capture+classify+measure there is no targeting and no proof a fix worked. The whole feature is the missing spine.

## Forces

- **Per-call cost.** The permission hook fires on *every* tool call. Always-on capture adds overhead, log noise, and — because it records command args — a privacy surface. → argues for **opt-in / off by default**.
- **Recurrence beyond permissions.** Prompt-capture is clearly the *first* thing one would diagnose; sandbox faults, egress denials, command timing, and error patterns fit the same observe→classify→report mold. → argues for an **extensible seam**.
- **Speculative-generality trap (COR-007).** With only one probe in hand we cannot validate a generic probe interface — we would be guessing at it. The same discipline just applied to the demo-recording capability (keep the seam internal, ship one instance, extract the framework when instance #2 recurs) applies here. → argues for **defer the framework**.
- **The signal already exists.** `decide.py` already computes a decision *and a reason* per call. The information needed to classify a prompt is produced at the moment of the prompt. → argues the **hook is the authoritative capture point**.
- **Per-project reality.** Each project's allowlist, sandbox state, and egress accommodations differ; a prompt in project A may be a non-event in project B. → analysis is **per-project**, with an optional roll-up.

## What is already known

- **COR-028** + the permission ADRs establish the model: ADR-002 (realizer ownership, fail-open, double-lock), ADR-004 (intent×confinement axes; allowlist-is-not-a-security-boundary; egress `enforcement: none`), ADR-005 (profiles), ADR-008 (confinement toolkits), ADR-014 (macOS Seatbelt / `uv` panic), ADR-015 (command-declared egress / allow-host), ADR-016 (capability-contributed grants), ADR-017 (confinement cannot override a harness-builtin deny).
- **The hook** (`permission-hook.py` → `decide.py`, `hook_decide` / `load_model`) is the single PreToolUse chokepoint; it resolves the subject (`agent:<type>` else default else operator) and returns allow / deny / defer. **Deferred == prompted** is the event we want to capture.
- **`fewer-permission-prompts`** (a shipped harness skill) already does a narrow version of this for ONE group: scan transcripts → propose an allowlist for common read-only Bash. This feature generalises that idea from one group + transcript-source to all groups + hook-source.
- **COR-007** is the governing discipline for *when* to extract the generic framework: at the second probe, not before.

## What's provisionally locked (this session's brainstorm)

1. **Signal source = the permission hook.** It already has the decision + reason; transcripts (+ `fewer-permission-prompts`) are a complementary cross-check, not the primary source.
2. **Opt-in, off by default.** A bounded "diagnostic session": `pkit permissions diagnose on|off`. Off (default) = one cheap flag check in the hook, nothing logged. On = append each deferred/prompted decision to a local log `{ts, subject, command, reason}`.
3. **Extensible seam, deferred framework (COR-007).** Ship one probe (permission-prompts) with a thin internal seam — *capture → sink → report* — factored but in-place. Extract a generic `diagnostics` home only when a second probe recurs. "Extensible" = probe #2 is a cheap add, not a framework built now.
4. **Home = permissions-scoped.** `pkit permissions diagnose …` (chosen over a standalone `pkit diagnose`); rename/extract at probe #2. The permissions capability already owns the hook that captures the data, so there's no cross-cutting concern yet to justify a separate home.
5. **The classification taxonomy** (the heart of "group them + suggest tasks") — seven groups, each with a remediation, split by who must act:

   | Group | Cause | Remediation | Class |
   |---|---|---|---|
   | allowlist-gap | safe command not in `permissions.allow` | add the pattern | auto-fixable |
   | egress | network host not accommodated | `sandbox accommodate <toolkit>` | auto-fixable |
   | sandbox-config | sandbox off while autonomy assumes on / escape-flag use | enable / fix sandbox | auto-fixable* |
   | interpreter | `python3`/`sed`/`awk`/`bash <file>` not allowed | allowlist it, or prefer a dedicated tool | needs-judgment |
   | write-scope | write outside workspace allowWrite | widen allowWrite (scoped) | needs-judgment |
   | shell-shape | `cd &&`/subshell/loop/heredoc the matcher can't vet | narrow single commands; extract a named project command (COR-007) | needs-judgment |
   | platform-limit | `uv`/Seatbelt panic (ADR-014); harness-builtin deny (ADR-017) | unfixable — document + route around | document |

   `pkit permissions diagnose report` ranks by frequency and emits per-group remediations; a later `report --fix` applies only the auto-fixable class. (*sandbox-config auto-fix is platform-gated — see ADR-014.)

## The `report` output (reference shape)

`pkit permissions diagnose report` — evidence-first, ranked, split by who must act:

```
$ pkit permissions diagnose report

Permission-prompt diagnosis — project: trustworthy-notes
  window: 2026-06-17 09:14 → 2026-06-19 16:40   (session diag-3f8a · 3 agent runs)
  captured: 47 prompts · sandbox: ON (lenient) · subject: agent:project-manager

── auto-fixable ─────────────────────────────────────────  31 prompts · 3 groups
 [1] allowlist-gap   22×   cd … && tn extract (14×) · npm run build (5×) · rmdir (3×)
     → add `cd` to permissions.allow   (rmdir → judgement: mutating)
 [2] egress           6×   curl api.anthropic.com (6×)
     → pkit permissions sandbox accommodate anthropic-api
 [3] sandbox-config   3×   dangerouslyDisableSandbox on `gh pr view` (3×)
     → recommendation only (posture change) — drop the escape flag

── needs your judgement ─────────────────────────────────  13 prompts · 2 groups
 [4] interpreter      9×   python3 scripts/gen.py (7×) · sed -i (2×)
     → allowlist `python3` (broad) OR route via `uv run` / a named command?
 [5] shell-shape      4×   for f in $(ls …) (3×) · heredoc → /tmp (1×)
     → narrow to single commands, or extract a named command (COR-007)

── can't fix — document & route around ──────────────────  3 prompts · 1 group
 [6] platform-limit   3×   uv run pkit … (macOS Seatbelt panic)  [ADR-014]
     → no allowance helps; avoid uv-in-box on macOS or run on Linux/bubblewrap

── summary ──────────────────────────────────────────────
  31 auto-fixable → `--fix` adds 1 allow pattern + 1 accommodation · est. −20/next window
  13 judgement    → 2 decisions for you   ·   3 documented → ADR-014 (no action)
  run `pkit permissions diagnose report --fix` to apply the auto-fixable band.
```

`--fix` is deliberately narrow — top band only, minus its risky items, and shows exactly what it changed:

```
$ pkit permissions diagnose report --fix
  + .claude/settings.json   allow  Bash(cd:*)
  + sandbox accommodate     anthropic-api   (egress → api.anthropic.com)
  applied 2 fixes · est. impact −20 prompts/window
  held for judgement: rmdir (mutating) · python3 · shell-shape   ·   documented: ADR-014
  → re-run a diagnostic session to confirm the decay.
```

Design choices: **evidence before verdict** (top commands + counts per group, so the classification is trusted); **the three bands are the action contract** (apply / decide / accept); **every group terminates in a concrete remediation**; **the `est. −N/next window` line is the re-measure promise** that closes the loop.

## The `--fix` boundary (resolved)

`--fix` applies only what it could justify to a security-conscious operator without asking; everything with a risk gradient becomes a proposed task. Gating is **per-item, not per-group**, within the auto-fixable band:

- **allowlist-gap** → auto-apply only commands on a known read-only/safe set (`cd`, `ls`, grep-likes). Mutating / guardrail-adjacent patterns (`rmdir`, `mv`, anything near `rm`/`sudo`) demote to needs-judgement.
- **egress** → auto-apply only when the host maps to a recognised shipped toolkit (anthropic-api, github-api, node, uv). Unknown host → judgement.
- **sandbox-config** → pulled OUT of auto-fix entirely; enabling/disabling the sandbox is a posture change (ADR-014 showed enabling-unattended can break the toolchain). Recommendation only.

Safety properties: writes **through the realizer** (settings merge primitive per COR-002, never a hand-edit); **idempotent** (re-run adds nothing); **records what it added** (reversible + auditable).

## Open questions (still to settle)

- **Cadence.** On-demand `report` command vs an end-of-session hook that auto-summarises vs a scheduled routine. (Leaning: on-demand `report` first; session-end summary later.)
- ~~Auto-fix boundary~~ — **resolved** (see "The `--fix` boundary" above): per-item risk gating within the auto-fixable band; sandbox-config demoted to recommendation.
- **Session-bounding.** How "on" auto-expires (TTL? session id? explicit off only?) so diagnostics can't silently stay armed and bloat the log.
- **Log location / format / retention / redaction.** Where the log lives (per-project under `.pkit/permissions/`?), its format (jsonl?), how long it's kept, and whether command args are redacted by default (privacy force).
- **Cross-project roll-up.** Prompts are per-project; whether/how to aggregate a portfolio-wide view, and where that would even run.
- **Relationship to `fewer-permission-prompts`.** Generalise it into this, wrap it, or leave it as the transcript-side cross-check that validates the hook-side log.

## Reviewer outcomes (critic → architect, 2026-06-19)

Headline: the **MVP — capture + classify + report-that-*recommends*, opt-in, no auto-apply — is architecturally clean** against COR-028 + ADR-002/003/004/016 and needs no authorisation. The refinements that reshaped the plan:

- **The original `--fix` was built on a wrong model (critic R1/R2).** The realizer is *model-driven*: it projects settings from grants of **named privileges in `privilege-catalog.yaml`**, not raw `Bash(cd:*)` patterns. `cd` / `npm run build` have no catalog privilege to grant, so `--fix` as drawn is fiction. Egress likewise — `accommodate` is toolkit-keyed (lockfile-detected), not host-keyed; auto-accommodating from an observed host is the ADR-004 "allowlist-from-traffic" anti-pattern.
- **The captured signal is "abstains", not "prompts" (critic G1).** Abstain = "defer to the harness"; the harness then runs its own allow/deny and may or may not prompt — the hook can't see that outcome, so capture **over-counts**. The abstain `reason` carries **no classification signal** → the classifier re-derives groups from raw command text. So the classifier is **advisory for ranking only**; a *safe-set* (not the classifier) gates any future fix, and `est. −N` downgrades to a **coverage** statement, not a prediction.
- **Capture placement (architect Q1).** Capture lives in the **adapter hook's `main()`**, after `hook_decide`, gated on `decision == abstain`, **fail-safe-wrapped** (a log-write failure must never change the decision or break fail-open). `decide.py` stays **pure** (same-code core, shared with the CLI). Classifier/taxonomy/report are **harness-agnostic** in the permissions surface. The gate-flag read is one cheap `stat` per call.
- **The `--fix` bright line (architect Q2 — escalation-flagged, deferred arc only).** Auto-apply is permitted **only for grants of already-cataloged privileges**; **authoring a new catalog privilege is never auto-fixable** — always a proposed operator task. The catalog is the operator-owned *trust vocabulary* AND the **guardrail-deny source file**; an agent minting privileges erodes the operator-owned *intent* declaration (it does **not** breach a security boundary — ADR-004 says the allowlist isn't one — intent erosion is the harm). Record **resolved-on-paper** now (ADR-002 #252 precedent) so a later builder can't slide catalog-authoring into the auto-fixable band.
- **It's a DEC, not a new ADR.** Sits within the COR-028/ADR-002/003/004 boundary; changes no ownership tier. MVP is a pure addition → bumps VERSION (PRJ-002), no COR-010 migration. Defer-the-framework (COR-007) confirmed; record probe #2 as the extraction trigger. The 7-group taxonomy stays in code/docs (inventory), NOT frozen in the DEC.

## Next step

Settle cadence + auto-fix boundary (the two that shape the command surface), then crystallise: a DEC for the diagnostic loop + opt-in posture, the hook instrumentation, and the `pkit permissions diagnose on|off|report [--fix]` command. Retire this note citing those.
