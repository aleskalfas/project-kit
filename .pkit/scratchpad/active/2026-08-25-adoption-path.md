---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-25
---

# Adoption path

*Adversarial usability effort: challenge pkit's adoption, collect problems + con-arguments honestly, fix one by one, repeat. Findings are recorded as the maintainer drives adoption on their own; the agent observes and records, does not smooth over.*

## Framing (maintainer's)

- **Roles to support:** project-manager + developer. Two adoption paths — may or may not be identical (TBD).
- **Two perspectives of adoption:**
  - *Technical* — use the tool without being a rocket scientist; quickly understand install / upgrade / init; understand the difference between the pkit CLI and the initialized pkit in a project.
  - *Mental model* — quickly grasp the basic building blocks and concepts.
- **The argument to defeat (honestly):** why use pkit instead of ad-hoc Claude-generated functionality in the project? Claude can be quite good at generating working things. For-pkit args (reusability, maintainability, …) do not win if the user can't quickly understand and use pkit.
- **Honesty signal:** a colleague stopped using pkit — it didn't fit him; he didn't even finish setting up the project.

## Loop

challenge pkit → collect problems + con-arguments → fix → challenge → collect → fix → …

## Findings

*(recorded as they surface: what I did → what I expected → what happened / what was confusing / the con-argument. Each is a candidate fix.)*

**F1 — Container-type taxonomy causes hesitation before any work is held.**
Did: as PM, tried to pick a container for the adoption effort. Expected: an obvious "put work here." Got: hesitation across EPIC/Feature/Umbrella/Task/Milestone; reached for Milestone "because it's more flexible" (i.e. EPIC felt rigid/heavy); unsure whether PM + developer roles even share a path. The type system makes "where do I put some work" a non-obvious up-front decision.

**F2 — "Milestone" is not the flexible bucket it sounds like.**
Did: `pkit project-management create-milestone`. Expected: create a lightweight flexible container. Got: requires a pre-declared `category` in `project/config.yaml` `milestone_categories:` (can't be created ad-hoc), carries close-trigger semantics, and the only declared category is "outcome bundle of related EPICs; closes when every child EPIC closes" — so it bundles EPICs, not Tasks. Flexibility intuition (dateless/content-based) is partially met, but the shape contradicts "put a task under it."

**F3 (meta) — Ceremony before value.**
Deciding merely *how to hold* the work required learning milestone categories, close-triggers, and the EPIC→Task hierarchy — up-front cost paid before any adoption benefit. This is exactly the asymmetry that loses a new adopter (cf. the colleague who quit before finishing setup).

**F4 — Milestone layer has no evident payoff in the single-EPIC case.**
Observed: if one EPIC holds all the tasks, the Milestone (declared shape: "bundle of EPICs") wraps a single child and adds nothing. Question raised by the PM adopter: "why have Milestones then?" The container hierarchy carries a layer whose value isn't self-evident until you have *multiple* EPICs to bundle — so a first-time adopter meets it as pure overhead. Candidate: guidance on when a Milestone earns its keep (≥2 related EPICs), or don't surface it in the basic path at all.

**F5 — EPIC is forced to kind `feature`; can't file a maintenance/usability EPIC honestly.**
Did: `create-issue --type epic --kind maintenance`. Got: refused — "epic/feature/umbrella carry kind 'feature' by definition." But this adoption effort is genuinely usability/maintenance, not a shipped feature. The taxonomy forces a semantic label that doesn't fit, so the classification lies (this EPIC is labelled `type:feature`). Candidate: allow non-feature kinds on structural clusters, or relax the restriction / document the rationale so it doesn't read as the tool mislabeling the work.

## Decision so far

Drop the Milestone. Use: **EPIC** ("make adoption clear & simple") → this discovery Task (hosts the scratchpad) + friction-fix Tasks. Scratchpad persists on the discovery Task's branch (commit + push), retires to `done/` at the end.
