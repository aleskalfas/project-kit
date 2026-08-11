---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-11
retired: 2026-08-12
produced:
  - DEC-049
---

# Audit journal model

Revisit the pm capability's audit/journal surface **as a whole** — define *why*, *when*, and *how* an audit-log comment is used — before fixing formats piecemeal. Prompted by #672, where the audit surface proved confusing and inconsistent.

## What prompted this

On #672: the `Todo→Backlog` transition produced **two** comments in different formats (a promote-issue hook comment *and* a move-issue `[audit]` line whose reason literally says "(audit comment already posted)"), while the `Backlog→In Progress` transition produced **no** comment and looked unlogged. And the posted `[audit]` line doesn't match the schema's own `audit_comment_template`. Three symptoms, one root cause: there is no single, stated model for what an audit comment is *for*.

## What exists today — three record surfaces

1. **GitHub labels + timeline.** The `state:*` label is the *live, authoritative* position; GitHub's timeline records every label add/remove (plus assignee, milestone, PR merge, review dismissal) with **actor + timestamp**, natively, no comment. This is already a state-change journal.
2. **Engine append-only journal** (`pkit process move` → `move-issue._journal_move`). A *local* record of every move; best-effort; **not on GitHub**. Invisible to someone reading the issue.
3. **Audit comments on the issue/PR.** Posted **only for bypassed / user-authorised (`bypassable-with-audit`) transitions** — to record the override reason.

## The load-bearing question — when is a comment actually needed?

GitHub's timeline already captures every label/assignee/milestone/merge change with actor + timestamp. So **a comment is redundant for anything the timeline already records.** An audit comment earns its keep only when it captures something the substrate **cannot**: the **why** behind an override/authorisation (the bypass reason), a human **attestation**, the cross-authority actor rationale. In other words:

> **Audit comments record *intent the substrate can't* — the justification for an override — not a duplicate state log. The timeline is the state journal.**

## Strawman policy (why / when / how)

- **WHY.** An audit comment preserves *intent the substrate cannot* — the reason a gate was overridden or authorised — so the justification survives even if the mutation later fails, and a reviewer can see *why*. It is **not** a state-change log.
- **WHEN.** Post an audit comment **iff** the mutation **overrode/authorised a gate that requires a recorded reason** — `bypassable-with-audit` bypasses (DEC-014), `--force` overrides (DEC-046), user-authorised transitions carrying a reason. **Do not** post for autonomous transitions the timeline already records (start-work `backlog→in-progress`, forward cascades) — the label event *is* the record.
- **HOW.** **One** canonical format from a single source of truth (the schema's `audit_comment_template`); **exactly one** audit comment per audited mutation (no wrapper + move-issue double-post); a consistent machine marker (`<!-- pkit-audit -->`) for filtering; actor (name + email / login), the transition, and the reason.

## The concrete debt to reconcile

- **Single source of truth for format** — `validation-severity.yaml`'s `audit_comment_template` (today `Bypassed by <name> <<email>>: <reason>`). Decide the final shape; make **every** poster use it.
- **Kill the double-post** — for `Todo→Backlog`, the promote-issue wrapper posts a hook comment *and* move-issue posts an `[audit]` line. One transition → one audit comment. Options: (a) move-issue is the sole audit writer and wrappers pass the reason through; (b) the wrapper suppresses move-issue's line.
- **`[audit]` line diverges from the template** — `[audit] transition 'todo' → 'backlog' bypassed with audit. Reason: …` vs the schema's `Bypassed by <name> <<email>>: <reason>`. Reconcile.
- **Marker consistency** — filing uses `<!-- pkit-provenance:filing -->`, verdicts `<!-- pkit-verdict -->`, hooks `<!-- pkit-hook: X -->`. Audit comments should carry a uniform `<!-- pkit-audit -->`.

## Discoverability of the state journal

The engine journal is local + invisible on GitHub; the timeline is the visible journal but users don't think to read it (exactly what happened on #672). Lean: **rely on the timeline as the state journal + document it**, and add a **read** command (`pkit pm history <N>`) that renders the full journal (timeline + engine) coherently — *not* more comments. Solving "I can't see the log" with a read surface, not by spamming the issue with state comments.

## Reframe — the governance boundary (maintainer point, 2026-08-11)

The strongest argument *for* logging pkit actions in comments is one neither the timeline nor a local journal gives alone: a **governance boundary**. A **provenance-stamped comment per pkit action** (carrying the pkit + capability versions) makes visible *which changes pkit governed vs which happened outside its control* — the timeline can't distinguish a governed `move-issue` from a hand-flipped label; the engine journal can, but invisibly. The *absence* of a pkit comment beside a timeline event flags an **ungoverned mutation** (the issue-tracker analogue of the COR-039 / rule-18 cross-repo interlock). This retracts the earlier "don't duplicate the timeline" stance — deliberate duplication buys the boundary.

The noise objection is resolved by **configurable intensity**, not by refusing to log:

- `off` — no journal comments (engine journal only).
- `audit` *(default)* — only override / authorisation comments (DEC-014 bypass, `--force`).
- `full` — every pkit-governed mutation as a provenance-stamped comment (governed-vs-ungoverned fully visible).

The **engine journal records everything regardless of level** — the knob controls only the GitHub *projection*. The boundary is *also* machine-detectable via `pkit pm history <N> --check-drift` (diff engine journal vs timeline → flag events pkit didn't author), so it works at any level.

**Revised spine for the DEC:** engine journal = canonical, substrate-neutral trail; GitHub comments = a **configurable, provenance-stamped projection** (`off` / `audit` / `full`); plus a **drift check** for governed-vs-ungoverned. Override comments (DEC-014) are the `audit` floor; `full` adds the complete governed trail.

## Open questions for the maintainer

1. **Format** — keep `Bypassed by <name> <<email>>: <reason>`, or richer (marker + transition + issue link)?
2. **Single poster** — make move-issue the sole audit-comment writer (wrappers pass the reason), eliminating the double-post?
3. **Autonomous transitions** — confirm **no comment** (the timeline is the record), rather than a lightweight per-move comment?
4. **History read** — is a `pkit pm history <N>` (renders timeline + engine journal) worth building to make the log discoverable without comments?

## Retirement (COR-012)

Produces: a **DEC** (pm capability) capturing the audit-comment policy (why/when/how/format), then implementation Features (reconcile format to the schema template, kill the double-post, uniform marker, optional `history` read). **Subsumes** the piecemeal #672 format-fix — that becomes one implementation slice under the settled policy.
