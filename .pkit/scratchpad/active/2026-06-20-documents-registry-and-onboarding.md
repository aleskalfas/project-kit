---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-20
---

# A documents-registry discipline + the capability brownfield-onboarding pattern

## The question

How should "continuous reliable documentation" work as a pkit discipline — adopter-customisable, opt-in (never pushed), with a per-repo root config that records every doc and *why it exists* — **reusing existing pkit systems, not inventing new mechanisms**? And is the one-time "prepare an existing project for a capability" step a general capability pattern?

## The opinion (the model)

A doc is *reliably continuous* when it is:

1. **Registered with intent** — a per-repo registry is the source of truth for *what docs exist and why each one exists*. The intent is declared, not implicit.
2. **Kept current** — every code PR must address docs (the mandatory `## Doc impact` gate, DEC-015); tight code↔doc couplings are enforced surgically (the code→doc mapping, #117 / ADR-019).
3. **Evolved under rules** — living-documents discipline (DEC-009): wording-free / scope-gated / ticked-sticky.
4. **Opt-in and dial-able** — the adopter chooses the level (registry-only → advisory → enforced → off) and can disable enforcement entirely. Never pushed (ADR-019 Case A posture).
5. **Mutated via tooling** — adding/retiring a doc goes through a command that edits the registry, not a hand-edit.

## Documentation convention (retro-derived)

How the existing docs emerged: organic accretion with **no governing convention** — each doc added on need, nothing governing the set. The mess types map 1:1 to a missing rule, so the convention is the diagnosis inverted:

| How the mess emerged (no rule) | The convention rule that prevents it |
|---|---|
| Same topic documented in several places | **One canonical owner per topic** — others *link*, never copy. |
| Docs written once, not maintained | **Living + currency-gated** — DEC-009 rules + `## Doc impact` gate + surgical code→doc mappings. |
| No declared purpose per doc | **Every doc registered with intent + audience + status** (the registry is the source of truth). |
| Mixed audiences / under-indexed clusters | **Audience-led taxonomy** (getting-started / concepts / subsystem / reference / ops / meta). |
| Contributor notes among product docs | **Product docs ≠ internal notes** — internal notes live outside the product set. |
| Generated + hand-authored blurred | **Provenance marked** — generated docs labelled; hand-authored carry a sync caveat. |

The consolidation's *target* is **conformance to this convention**, not just tidiness; the registry entry per doc *encodes* it (`path` + `intent` + `audience` + `status` + `canonical_owner` + `provenance`).

## The mapping to existing systems (do NOT invent)

| Want | Existing pkit system to reuse |
|---|---|
| Root config holding all docs + their intent | The **workstreams registry** shape (DEC-018): a storage `.yaml` of entities with a multi-attribute model + status. A `documents` registry is the same, new subject — entry = `path` + **`intent`** + `audience` + `status` + optional code-coupling. |
| A script that adds a docs area + edits the root config | The **workstream lifecycle tooling** (DEC-018): verb-subject commands (`add-workstream`, `edit-workstream`, `list-workstreams`, …). Docs equivalent: `add-doc` / `edit-doc` / `list-docs` / `retire-doc`, membership-gated. |
| Adopter can disable / opt-in enforcement | The **`enforce` toggle** already built (#117 / ADR-019), opt-in / default-off. |
| Keep code & docs in sync | The **code→doc mapping** (#117) + the **`## Doc impact` gate** (DEC-015). |
| Rules for evolving a doc | **living-documents (DEC-009)** — today scoped to *issue bodies*; widen the concept to *project docs* (same rules, new surface — a small extension, not a new decision). |

The only genuinely-new thing is **applying the workstreams registry+tooling pattern to a new entity (documents).**

## The meta-pattern (forward pointer — extract later, from instances)

Two recurrences are now visible; both want generalising eventually, *from the instances, not speculatively*:

- **Registry + verb-subject lifecycle tooling** — workstreams (instance 1), documents (instance 2). A reusable "registry-backed entity" pattern.
- **Capability brownfield-onboarding** — adopting a capability on an existing project needs a one-time step that brings existing state into the enforced shape. PM ships `bootstrap` (prerequisites, DEC-017) + back-fill (consolidate legacy issues); docs need consolidation; evidence needs back-fill. The shared part is a *convention* (a `bootstrap`/onboarding command + an onboarding skill for judgment-heavy consolidation; idempotent; per-capability mechanics), like COR-005's pairing. Crystallise as a COR / COR-017 amendment once the docs instance teaches its shape.

## Audit log = diagnosis + golden baseline + tool-report spec

The manual spike records every change as a structured **audit log** (`2026-06-20-igw-docs-consolidation-audit.md`), per change: docs touched · convention-rule violated · what was wrong · what was done · resulting registry entry. It serves three roles at once:

1. **Complete diagnosis** — nothing forgotten; the "how it emerged" picture is exhaustive.
2. **Golden baseline** — when the crystallised tool re-runs on the *original* state, diff its changes against this baseline (golden-file validation: does the tool reproduce the human judgement?).
3. **Tool-report spec** — a consolidation/bootstrap tool *should emit exactly this shape* (found-wrong → did → registry entry). The manual log is the spec for the tool's output. (Reinforces the brownfield-onboarding pattern: the onboarding step produces an auditable report, not just silent edits — same posture as the permissions diagnose `report`.)

## The plan

1. **IGW docs-consolidation spike** (separate branch, "sharpen the tools") — do the consolidation by hand, and for each surviving doc **record what its registry entry would hold** (path + intent + audience + status). The spike teaches the registry model.
2. **Re-run from fresh** on the pre-consolidation state to **prove it reproduces** — the real validation.
3. **Crystallise** the `documents` registry + `add-doc` tooling (cloned from workstreams) + wire to the #117 gate; widen DEC-009 to project docs; then extract the general onboarding/registry meta-patterns from the two instances.

## IGW deep-read findings (the proving-instance input, 2026-06-20)

Product purpose (lead with this): *a sandbox both humans and AI agents drive through one shared recording-and-replay I/O path, so human and AI runs of the same task are captured in the same typed trace and replay byte-for-byte for comparison.*

The set is **well-organised already** (`docs/README.md` is a strong task-oriented index — not flat sprawl). The work is **de-dup + de-stale + reconcile**, not reorganisation:

- **Merge** `SANDBOX_CONNECTION_MODEL-SIMPLIFIED.md` into `SANDBOX_CONNECTION_MODEL.md` as a "Simplified 3-channel variant" section (largest duplication/drift surface).
- **De-duplicate `INTEGRATION.md`** (1185 lines) — strip the copied MCP_TOOLS migration/trace tables; link the canonical owners.
- **Trim `PERSONA_HARNESS`** mode/pane tables to pointers at `WORKBENCH_MODES`; fix "four modes" (lists three).
- **Resolve the `panes:` required-vs-synthesised-default contradiction** across PANE_LAYOUT + the harness docs.
- **Sweep tool-name drift** (`mcp__igw__*` → `mcp__operator-*`) across INTEGRATION + OPERATOR_HOST + MCP_TOOLS.
- **Hygiene:** SMOKE_TEST (three colliding "Path H" sections; stale `0.1.0` pin), CHANGELOG (lingering `Unreleased`, missing compare-links), WORKFLOW ("no CHANGELOG today" line is stale).
- **Relocate** `docs/diagrams/mermaid-style.md` out of product docs (internal contributor note; cites non-existent lint tooling).
- **Keep despite their names:** DEBUG_LOG (feature reference) and SMOKE_TEST (manual-QA walkthrough) are durable, not ephemera.

Suggested audience-led taxonomy (survivors): getting-started · design/concepts · subsystem-guides · reference/contracts · integration & operations · project-meta · (out: mermaid-style).

## Lifecycle

Retire to `done/` when the documents-registry + `add-doc` tooling crystallise (cite them) and the onboarding/registry meta-patterns are recorded; or drop if the discipline is abandoned.
