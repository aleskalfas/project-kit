---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-07-01
---

# Autonomy friction: generalizing the compound-elimination pattern beyond project-manager

Exploratory note (COR-012). Retires by producing an ADR/COR decision, or being dropped. It does **not** pre-decide the generalization — it frames the question and the evidence gate. Escalated by EPIC #315 ("a reusable cross-project permission-friction analyst agent — no valid COR-026 home yet; needs an architectural call"); feeds EPIC #426 and its characterization Task #429.

## The question

Two coupled facets of one decision:

1. **Placement (COR-026).** Where does *cross-project / cross-agent permission-friction analysis* live? The cross-repo diagnosis this note stands on was a manual analyst pass (read the diagnose logs, classify, rank, recommend). If that analysis is worth making a reusable capability/agent, [COR-026](../../decisions/core/COR-026-agent-placement-by-discipline.md) says it lives in the capability that ships the discipline — not a generic home. Is there such a home, or does the friction-analysis discipline warrant a new capability?

2. **Recurrence (COR-007).** Does the *butter-verb / clean-output compound-elimination* pattern generalize beyond `project-manager` to other agents (e.g. the `se-*` software-engineer agents)? [COR-007](../../decisions/core/COR-007-pattern-extraction.md)'s threshold is recurrence *observed* (~2–3 worked instances), not anticipated. Today there is exactly **one** proven instance — `project-manager` via EPIC #315 / #335 (the `show-*` read redirect + targeted mutation verbs). Extracting a reusable pattern off one instance is the premature-abstraction failure COR-007 names.

The two are coupled: the friction *analyst* (facet 1) is the tool that reveals *where* butter-verbs are needed; the *generalization* (facet 2) is applying the pattern the analyst surfaces. #315 escalated them together.

## Forces

- **The evidence is loud but not yet decisive.** Cross-repo diagnosis (6 repos, ~1,876 captured deferrals → ~763 real prompts): compound shell is ~75% of real prompts across *all* agents and repos — so the friction is clearly not project-manager-specific. But volume of *friction* is not the same as a *second worked butter-verb instance*: we have evidence the problem generalizes, not yet evidence the *solution shape* does.
- **Superset caveat.** Those figures are a superset of real prompts (the diagnose hook sees its own abstain, not the harness's final prompt), measured on stale pre-propagation logs. A fresh baseline (#429) is the honest input.
- **Least-privilege (COR-028 / ADR-004).** Any generalization must not reach for "broaden the default grants" — the deny-by-default posture is load-bearing. The pattern is *eliminate the compound at the source*, not *widen the allowlist*.
- **Acceptance gate.** No dependent work (a generalization Feature, a new analyst agent) may be authored until this crystallises into an accepted decision.

## What is already known

- **One worked instance.** `project-manager`'s compound elimination: reads redirected to clean-output `show-*` verbs (raw `gh view|diff` denied), plus targeted `check-criterion` / `set-field` mutation verbs, so the pipe-carrying command shapes vanish from the diagnose report. Measured by the diagnose oracle (#335).
- **The mechanism for placement already exists** where a home is found: capability-scoped agents (COR-026), capability privilege-catalog fragments (ADR-021), and each agent's grants fragment. What is *missing* is the discipline's home, not the wiring.
- **`se-*` agents are the candidate second site.** Observed in an adopter (trip-planner-agent-data): multiple software-engineer agent subjects, compound-heavy. They are shipped by a software-engineering capability — which, per COR-026, is where *their* butter-verbs would live, if the pattern generalizes.

## Candidate directions (not yet chosen)

**Facet 1 — friction-analyst home:**

- (1a) A **new `permissions`-adjacent capability** owning the diagnose→analysis→recommendation loop (the manual pass this note came from, made reusable). Coherent if the analysis discipline is genuinely cross-cutting.
- (1b) **Fold the analysis into the existing diagnose tooling** (the `report` already classifies compound-vs-gap) — extend the report rather than stand up an agent. Cheaper; may be sufficient if "analysis" is really "a sharper report."
- (1c) **No reusable analyst** — the manual pass is rare enough that tooling is premature (COR-007 applied to the *analyst itself*: one manual pass is one instance).

**Facet 2 — butter-verb generalization:**

- (2a) **Per-capability butter-verbs** — each agent's discipline capability ships its own clean-output/targeted verbs (COR-026-consistent). No shared abstraction; the *pattern* is a documented convention, not extracted code.
- (2b) **A shared butter-verb substrate** — extract common machinery (clean-output redirect, targeted-mutation verb shape) once, capabilities consume it. Only justified at ≥2 clean instances with genuinely shared shape.
- (2c) **Defer** — hold until a second capability independently needs it.

## What would resolve this

- **The COR-007 gate:** a *second* clean butter-verb instance in a different capability (e.g. `se-*` reads/mutations redirected to clean verbs), characterized from the fresh diagnose baseline (#429). Two instances with a genuinely shared shape → (2b) extraction is earned; two instances with divergent shapes → (2a) per-capability convention; no second instance yet → (2c) defer.
- **The COR-026 gate:** identify the discipline's owning capability. If the friction-analysis discipline is real and cross-cutting → a capability home (1a); if it is "a better report" → (1b); if one-off → (1c).

Until then: **no generalization Feature, no analyst agent is filed** — #429 produces the second-instance evidence, and this note crystallises into the ADR/COR that the evidence supports.
