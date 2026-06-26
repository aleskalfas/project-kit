---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-25
---

# Permission friction butter

Working draft for an EPIC. Retires by producing the EPIC + child tickets (+ pm DECs).
Reviewed adversarially by `critic` + `architect` (2026-06-25); plan reshaped below.

## Problem

`project-manager` repeatedly needs operator confirmation during ordinary issue
work. Root cause is **not** missing permissions — its commands are individually
allowlisted. The prompts come from **compounds**: allowlisted command +
`cd … &&` prefix + `| grep / tail / sed` suffix, which the permission hook can't
vet as a unit → it abstains → the harness prompts.

We eliminate the compound **at the source** with intent-shaped commands, rather
than teach the permission layer to decompose pipelines (deferred — see below).

## Evidence (mined from 4 diagnose logs)

Samples + miner: `./permission-friction-butter-samples/`.

- All 20 `pkit project-management` deferrals for `project-manager` were piped (20/20).
- Pipe targets (all subjects): `tail 229 · grep 168 · head 136 · sed 12 · awk 9 · wc 8`
  → dominant cause is **output truncation/filtering** (~90%), not input surgery (~10%).
- Surgery signal: `edit-issue #239 ×2, #240 ×2`; manual `sed ×4`.
- Heaviest reads then grepped: `gh issue view 16 · gh pr view 12 · gh pr diff 9`.

## What the reviewers corrected (load-bearing)

- **The read commands already exist.** `show-issue.py`/`show-pr.py`/`show-tree.py`
  ship today with `--json` + terse output (verified). The agent bypasses them
  with `gh … | grep`. So the read side is *adoption*, not a build.
- **A rule won't fix adoption.** `core.md` rule 15 already forbids composing /
  mandates dedicated tools; the agent ignores it. Redirect must be **structural**.
- **The mutation gap is real.** `edit-issue.py` is whole-body-only
  (`--body/--body-file/--append/--title`) — targeted `check-criterion`/`set-field`
  genuinely don't exist. (`--append` half-covers `add-note`.)
- **Output filtering is ~90%, surgery ~10%.** Composite `edit` (#6) had *zero*
  supporting evidence → deferred. The analyst agent has *no valid home*
  (COR-026 has no slot for a backbone-permissions-implying agent; "permissions
  capability" doesn't exist — it's backbone code) and fails COR-007 (ran once)
  → deferred + escalated.
- **Carriers are pm DECs, not ADRs.** "Butter command" is a *discipline*
  refining DEC-020 (intent-shaped I/O over the existing substrate-primitive
  layer), not a new layer. The analyzer *extends* `pkit permissions diagnose
  report`, not a new `analyze`. Composite-edit semantics must be
  validate-up-front + idempotent-recovery (GitHub has no transactions).

## Reshaped plan (EPIC + children)

**EPIC — Make `project-manager` issue work prompt-free: clean-output adoption + targeted-mutation verbs.**

- **W1 — Baseline + oracle (first).** Extend `pkit permissions diagnose report`
  with an "allowlisted-but-compound vs genuinely-missing" classification axis;
  verify the log distinguishes *prompted* vs *auto-allowed* outcomes. This is the
  regression oracle for everything below. Confirm the baseline post-dates ADR-025
  (cd-strip) so credit lands on the butter verbs, not the strip.
- **W2 — Read redirect (structural, not a rule).**
  - W2a: add `--field <x>` targeted output to `show-issue`/`show-pr` (so the
    agent asks for the one field bare — nothing to `grep`).
  - W2b: scoped deny of raw `gh issue view` / `gh pr view` / `gh pr diff` for
    `agent:project-manager`, with a redirect message to `show-*`. A deny is
    auto-rejected (no operator prompt); the agent adapts. Narrow scope —
    `gh pr checks`/`gh run` stay allowed.
- **W3 — The real mutation gap.**
  - W3a (decide first): a pm **DEC** for criterion addressing (index vs stable-id
    vs text-match). Stable-id touches the body schema (DEC-010/007/009) → a
    `schema_version` bump + COR-010 migration. Index/text-match is fragile on
    reorder. Resolve before building.
  - W3b: implement `check-criterion`/`uncheck-criterion` + `set-field` as
    **batch-capable substrate primitives** (per DEC-020), governed by a DEC that
    pins the intent-shaped I/O discipline + the validate-up-front/idempotent
    failure stance.

**Deferred (tracked, not now):**
- Composite `edit` transaction — no evidence yet; revisit when surgery sequences appear.
- `permission-friction-analyst` agent — **escalated**: needs an architectural call
  on its home (COR-026 refinement, or stand up a permissions capability). Recommend-only.
- Pipeline-decomposition in `decide.py` — long-tail safety net; consistent with
  ADR-025 deliberately leaving pipe handling to source-elimination.

## Carriers (stamp once each fork settles)

- Butter-command I/O discipline + discriminator → pm **DEC** refining DEC-020.
- Criterion addressing → pm **DEC** (+ migration if stable-id).
- Composite `edit` failure semantics → pm DEC (validate-up-front + idempotent-recovery).
- `--json`/`--field` consumed-output shape → capability `schemas/*.schema.json`.
- Analyst-agent home → **COR-026 refinement** (escalation).

## Verification

After each workstream: re-arm `pkit permissions diagnose`, run ordinary issue
work, re-run the report — the targeted family should be absent. Samples here are
the before-baseline.

## Outcome (2026-06-26)

EPIC #315 filed with five children; all merged this session, each through the
full gate chain (producer → convention-compliance / methodology → reviewer →
CI):

- **#317 W1** (PR #322) — diagnose report sharpened with the prompted-vs-auto-allowed
  and compound-vs-missing axes. Baseline read: **87 real prompts of 222** captured
  (135 auto-allowed false positives), **72 allowlisted-but-compound**, 15 genuinely-missing.
- **#318 W2a** (PR #327) — `--field` targeted output on `show-issue`/`show-pr`.
- **#319 W2b** (PR #329) — read-redirect deny (`issue-tracker-read-raw`) routing
  `agent:project-manager` from raw `gh issue/pr view|diff` to the clean verbs.
- **#320 W3a** (PR #331) — **DEC-038** authored + accepted (index addressing + optional
  text guard; validate-up-front + idempotent-recovery).
- **#321 W3b** (PR #334) — `check-criterion`/`uncheck-criterion`/`set-field` batch
  primitives; dogfooded to tick its own acceptance criteria.

**EPIC #315 remains open at 3/4 success criteria.** The fourth — the before/after
proof that ordinary issue work now produces zero operator prompts for the targeted
families — is genuinely pending: it needs a *fresh* post-fix diagnose capture from
real working sessions, which can't be fabricated. The before-baseline is the
`permission-friction-butter-samples/` here. To close it: re-arm `pkit permissions
diagnose on` at the start of a real working session, work normally, then
`pkit permissions diagnose report` and confirm the read families and the piped-
`pkit` compound families have dropped.

### Findings surfaced by dogfooding (candidate follow-ups)

1. **The close-gate gates *all* checkboxes, but `check-criterion` only addresses
   the `## Acceptance criteria` section.** A `## Doc impact` checkbox (or any box
   outside acceptance criteria) still needs the whole-body `edit-issue` path —
   observed closing #321. Either widen the verb's addressed sections or document
   the boundary.
2. **The criterion extractor recognises `## Acceptance criteria` but not an EPIC's
   `## Success criteria` heading** — so `show-issue 315 --field criteria` returns
   empty for an EPIC, and `check-criterion` can't address EPIC success boxes.
   Worth teaching the extractor the EPIC heading.

Deferred items remain unfiled by design: composite `edit`, the
`permission-friction-analyst` agent (COR-026-home escalation), and
pipeline-decomposition. The two findings above are new.
