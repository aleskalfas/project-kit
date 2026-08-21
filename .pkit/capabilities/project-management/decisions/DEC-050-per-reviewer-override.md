---
id: DEC-050
title: Per-reviewer override on the merge gate
status: proposed
date: 2026-08-21
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> Let an operator satisfy **one** required reviewer's slot on the merge gate with an audited **`done-work --bypass-reviewer <name> --bypass-reason "<r>"`** (repeatable), instead of today's only escape — discarding the *entire* gate with `--bypass`. The named reviewer's slot counts as **satisfied-by-override** (a first-class state, *distinct* from a real `APPROVED`); every other required reviewer still gates. This is the false-block safety valve [software-engineering:DEC-002]'s panel requires: without it, one over-eager reviewer trains the blanket-bypass reflex (#715 from the other side). Ephemeral (a merge-time flag, like `--bypass`), audited (a prose comment recording who/which/why, kept off the verdict stream), and extends [project-management:DEC-046]'s `--bypass` family. It **widens [project-management:DEC-032] D3's satisfaction predicate** (amended in place) — a foundational, maintainer-authorised change.

## Context

The merge gate is all-must-approve over a per-PR resolved required-reviewer set ([project-management:DEC-028], [project-management:DEC-032] D3). Today the only override is the whole-gate `--bypass` ([project-management:DEC-014] bypassable-with-audit). [software-engineering:DEC-002] ships a code-review *panel* (multiple required reviewers) and names a per-reviewer override as a required companion — because under all-must-approve a single over-eager reviewer blocking the merge leaves the operator only the whole-gate bypass, which discards *all* review and retrains exactly the "green means nothing" reflex #715 is about. This DEC realises that companion. Its gate-predicate widening was authorised by the maintainer (the architect's escalation, AC-1).

## Decision

**Add a per-reviewer override to the approval gate: an operator satisfies one named required reviewer's slot with an audited reason, leaving every other required reviewer gating.**

1. **The gesture: `done-work --bypass-reviewer <name> --bypass-reason "<r>"`, repeatable.** It lives on `done-work` — where the approval gate and the whole-gate `--bypass` actually are — not `merge-pr` (which runs only membership/checkbox/title/CI gates). It **extends [project-management:DEC-046]**'s `--bypass[-<gate>]` family with a *parameterised, repeatable* target (DEC-046's suffix was a fixed gate name; a reviewer name is a parameter) — it is a member of the bypass family, not a new `--override-*` verb.
2. **Satisfaction: a first-class `satisfied-by-override` state.** [project-management:DEC-032] D3's per-reviewer conjunct is amended in place so a reviewer is satisfied by *(a fresh `APPROVED` on any registered path) **or** (satisfied-by-override)*; AND-across-the-set is unchanged. `satisfied-by-override` is **not** a synthetic `APPROVED` — it is a separate gate-checker input, so it never corrupts the DEC-028 verdict record or the [ADR-042] read surface.
3. **Ephemeral, merge-time flag.** The override is evaluated once, at the invocation, against the *currently* resolved set and current HEAD — exactly like `--bypass`. It is **not** a persisted signal a later `done-work` run reads back (that would need commit-freshness and risk "override once, merge anything forever"). A new commit / reclassification / diff change simply re-resolves; the operator re-supplies the override if still intended.
4. **Audited, off the verdict stream.** Before the merge it posts a bypassable-with-audit comment (DEC-014 shape) recording: the overridden reviewer, the operator (name + email), the reason, **and the reviewer's state at override time** (`none` / a fresh `CHANGES_REQUESTED` / a stale `APPROVED`) with a pointer to the block comment if one exists. The comment is **prose, verdict-grammar-distinct** — no `Reviewer agent:` first line, no `<!-- pkit-verdict -->` marker — so neither the gate's verdict reader (DEC-028 as amended by DEC-047) nor ADR-042's read surface ever mistakes it for a verdict. A per-reviewer(+reason) idempotency stamp lets a re-run overriding a *different* reviewer, or the same reviewer with a *different* reason, post its own audit.
5. **Validated against the freshly-resolved set.** `--bypass-reviewer <name>` where `name` is **not** in the freshly-resolved required set is a **hard error** naming the resolved set (catches a typo, or a name dropped by reclassification/uninstall) — not a silent no-op. When the set is *unresolvable* (broken contribution / undeployed agent), the override cannot help — that is the whole-gate `--bypass`'s job. The override operates **within** a resolved set.
6. **Soft all-slots nudge.** Overriding *every* slot equals the whole-gate bypass by other means — allowed (it is audited, consistent with the honor-system trust model), but the command **warns** and steers the operator to `--bypass` (one audit, the honest tool) rather than N per-reviewer bypasses. A warning, not a refusal.

**Amends [project-management:DEC-032] D3 in place** (the satisfaction predicate gains the `satisfied-by-override` OR-branch) and **extends [project-management:DEC-046]** (the parameterised bypass-family member), per the precedent DEC-032 set amending DEC-028 steps 6–7 — both land when this DEC is accepted.

## Rationale

**Why per-reviewer, not whole-gate only.** Under a panel, one false block otherwise forces `--bypass` — discarding *all* review and training the blanket-bypass reflex. A per-reviewer override waves off the one, keeps the rest gating, and is *more* legible (per-reviewer name + reason vs one blanket reason). It is the safety valve software-engineering:DEC-002's block-only-on-objective discipline pairs with — an LLM reviewer is not perfectly tunable, so a per-PR valve is necessary however well thresholds are set.

**Why `satisfied-by-override` must be a distinct, first-class state.** For the honest gate summary (software-engineering:DEC-002's companion (c)) to show "*N reviewed, 1 overridden*" rather than "*N approved*" — else #715's false-green returns from the other side — the override must be a state the gate-checker records distinctly, **not** a fabricated `APPROVED` comment (which would corrupt the DEC-028 verdict record and ADR-042's read surface). The distinct state is *necessary but not sufficient*: it enables that summary once companion (c) lands; until then the **audit comment (Decision 4) is the interim honesty surface**. Hence a separate gate-checker input + a verdict-distinct audit comment.

**Why ephemeral.** A merge-time flag sidesteps every persistence race by construction — nothing survives to a later run, so a diff or set change between runs just forces a fresh, re-audited override. A persisted override would be *more* dangerous than `--bypass`.

**Why audit-per-override is enough.** DEC-028/DEC-032 frame the whole gate as attestation, not security, with GitHub branch protection as the enforcement floor; DEC-014's reason-required, comment-before-mutation is the sanctioned in-band override. A hard guard is unneeded — but the all-slots nudge keeps the honest tool (`--bypass`) in view.

**The override trail is the retune signal.** Override-frequency per reviewer identifies the *over-blocking* agent to retune — so the override is complementary to threshold-tuning, not a worse substitute: tuning fixes the systemic rate, the override handles the residual per-PR false block *and* produces the evidence for the next tuning pass.

### Alternatives considered

- **Whole-gate `--bypass` only** (status quo). Rejected — one false block discards all review and trains the blanket-bypass reflex (the software-engineering:DEC-002 concern).
- **A new `--override-*` flag family.** Rejected — DEC-046 fixes the `--bypass[-<gate>]` family for bypassable-with-audit gates; a fourth verb for the same concept invites conflation. This is a `--bypass` family member.
- **Non-overridable ("hard") reviewers** (e.g. an un-overridable `security-reviewer`). Rejected — reintroduces the veto that trains the blanket bypass; software-engineering:DEC-002's philosophy is block-only-on-objective *plus* an always-available valve. Uniform overridability.
- **A persisted override signal the gate reads on later runs.** Rejected — needs commit-freshness and risks "override once, merge anything forever." Ephemeral flag instead.

## Implications

- **`done-work` gains `--bypass-reviewer <name>` (repeatable) + `--bypass-reason`.** The gate-checker gains the `satisfied-by-override` OR-branch on DEC-032 D3's per-reviewer conjunct; unknown-name → hard error; all-slots → warn.
- **Audit comment** is prose, verdict-grammar-distinct, with a per-reviewer(+reason) idempotency stamp, posted before the merge (DEC-014).
- **Amends DEC-032 D3 in place** and **extends DEC-046** (both amended when this DEC is accepted, per the DEC-028-steps-6–7 precedent).
- **Depends on the honest gate summary** (software-engineering:DEC-002 companion (c), a sibling Task) to *render* `satisfied-by-override` distinctly — this DEC produces the state; that Task surfaces it. Shipped without it, the override still audits but the summary line is not yet honest.
- **Grammar dependency:** the overridden state's fidelity rests on a reviewer's block being machine-legible — the block token is `CHANGES_REQUESTED` (DEC-028; software-engineering:DEC-002 corrected to match). There is no "override a `REJECTED`" case: a *block* being overridden is a fresh `CHANGES_REQUESTED`, distinct in the audit from overriding an absent verdict or a stale `APPROVED` (the three states Decision 4 records).
- **Acceptance gate:** no `--bypass-reviewer` code ships until this DEC is `accepted` (rule 2). Authored here; accepted before the implementation lands.
- **Surface change** ([PRJ-002]) → a `project-management` changeset. **Migration-free:** additive — no override supplied = today's behaviour.
- **ADR:** not warranted unless the override-signal primitive proves non-obvious (the ADR-042 situation) — decided at realization, not here.
- Stands on DEC-028, DEC-032, DEC-014, DEC-046 (all accepted) and realises the software-engineering:DEC-002 companion.
