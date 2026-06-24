---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-24
retired: 2026-06-24
produced:
  - DEC-037
---

# Brownfield adoption ceremonies — attribute auto-population, hooks, presets

Design exploration (COR-012). Captures the **adoption-ceremony / write-side** of
brownfield adoption, which [DEC-036](../../capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md)
+ ADR-026 (the substrate-map *read-path* contract) deliberately scope OUT. ADR-026
answers "how pm resolves an axis through the map at runtime"; this note is about
"what one-time + ongoing ceremonies run when a brownfield repo is adopted."

## The question

Adopting a brownfield repo isn't only passive read-mapping — the adopter needs
**scripts that POPULATE attributes** across the issue corpus, with adopter-specific
values pkit would never ship. Grounding case (AUJ):

- every existing issue's Projects-v2 `workstream` field should be set to **`Spyre`**
  (an adopter-specific value, not a kit vocabulary);
- all issues should get a **time-based milestone** assigned.

How should pkit support adopter-supplied attribute population at adoption — as a
**hook/script slot the adopter fills**, run through an **auditable** ceremony, with
**presets** harvested from real adopters — reusing existing pkit systems, not
inventing new ones?

## Two distinct sub-parts

1. **Back-fill the existing corpus (one-time, at adoption).** "Set
   `workstream=Spyre` on all N issues; assign milestone X to the set." This is a
   **`migrate`-style bulk transform** — it belongs in pm's existing
   bootstrap/migrate family ([DEC-017](../../capabilities/project-management/decisions/DEC-017-prerequisites-bootstrap-migrate-discipline.md)),
   NOT the substrate-map. **Load-bearing safety:** bulk-mutating hundreds of real
   issues MUST run through the **auditable propose-and-cite report** (the
   brownfield-onboarding posture — propose the changes, cite why, human confirms,
   then apply; never silent mass-edits). Same posture as the permissions `diagnose`
   report and the IGW docs-consolidation audit log (living-docs #234).

2. **Default new issues going forward.** `create-issue` auto-populates
   `workstream=Spyre` (and any other adopter defaults). This is a **per-axis
   `default:`** — a small addition to the substrate-map alongside the binding, OR a
   create-issue **hook**. Persistent, declared once. (Note: this is the *write/seed*
   complement to ADR-026's *read* resolution; the sole-constructor seam in ADR-026
   is the natural place a default value is emitted on a write path.)

## Mapping to existing systems (reuse, don't invent)

| Want | Existing pkit system to reuse |
|---|---|
| One-time bulk back-fill of existing issues | `migrate` discipline (DEC-017) + the auditable propose-and-cite report (the brownfield-onboarding meta-pattern, #217/#234) |
| Adopter-supplied population logic (the `Spyre` value, which milestone) | a **hook/script slot** the adopter fills — relates to the deferred **`hooks`** slot (parked in EPIC #237); pkit ships the slot, the adopter authors the content |
| Default attribute on every NEW issue | a per-axis `default:` in the substrate-map (DEC-036), emitted through ADR-026's sole-constructor seam on the write path |
| Scaffolding the ceremony from the live repo | the deferred **`adopt-existing`** tool (DEC-036 deferred it) — inventory + draft the map + draft the population scripts |
| Common adopter shapes | **presets** (below) |

The genuinely-new things: (a) adopter-supplied **population hooks** run at adoption,
and (b) **presets**.

## Presets (harvested from instances, not speculative)

A small library of adoption recipes for recurring adopter shapes, each bundling
substrate-map + default values + back-fill/population scripts. E.g. *"GitHub repo
with `P0/P1/P2` priority labels + `[Task]`/`[Epic]` title-prefix types + a
Projects-v2 workstream field"* → a ready preset the adopter tweaks (set the
workstream value, pick the milestone). **Extract-from-instances** (COR-007): harvest
presets from real adopters (AUJ, trip-planner) once they adopt — do not author
speculative presets ahead of a real shape.

## Boundaries (what this is NOT)

- **NOT ADR-026.** That is the runtime read-path; this is the adoption-time
  write/populate ceremony. They compose (the per-axis `default:` is emitted through
  ADR-026's seam) but are separate decisions.
- **NOT a silent mass-edit.** Any bulk write over existing issues goes through the
  auditable report — non-negotiable (it mutates real adopter data).
- **NOT the cross-capability bootstrap COR.** The auditable-report ceremony is part
  of the shared greenfield/brownfield bootstrap meta-pattern (#217 pm + #234
  living-docs), which extracts to a core COR on the second instance. This note is
  pm's adoption-ceremony instance feeding that.

## Plan / retiring this note

Feeds a future **adopt-existing / population Feature** under EPIC #217 (Wave-2),
the same way the `pm-brownfield-adoption` note fed DEC-036. Retire to `done/` when
it produces that Feature's spec (or a DEC if the hook/default mechanism needs one),
or drop if abandoned. Cross-refs: DEC-036 + ADR-026 (read-path), DEC-017
(bootstrap/migrate), EPIC #237 (`hooks` slot), EPIC #217 (Wave-2),
EPIC #234 + the shared-bootstrap thread (the auditable-report meta-pattern).
