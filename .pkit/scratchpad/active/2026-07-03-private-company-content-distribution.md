---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-07-03
---

# Private, company-internal distribution of adopter-owned content

*Exploratory (COR-012). Maps a design area that surfaced across a single design conversation on 2026-07-03: three separately-raised adopter needs that turn out to be faces of one underlying question. Non-normative — this note weighs the space; the decision(s) crystallise later. Does not block, and is distinct from, the release + versioning arc under EPIC #332 (though it composes with it — see "Composition" below).*

## The question

How does a company **privately share adopter-owned pkit content across its own repositories** — content it does *not* want to publish to the public kit, but does want to maintain in one place and consume everywhere internal? "Adopter-owned content" here spans two forms that arrived as separate asks but share one mechanism:

1. **A whole capability** the company authors and keeps private (proprietary discipline).
2. **An overlay / profile on a kit-shipped capability** — a company-standard `project/` bundle (config + workstreams + hooks + templates + overlays) that customises, e.g., `project-management` to house conventions *without forking it*.

## Why now — the grounded consumer

The `externally-sourced` capability origin was **reserved but deliberately unbuilt** in [COR-031](../../decisions/core/COR-031-capability-origin.md), and its mechanism deferred to [EPIC #131] — both explicitly gated on a *grounded consumer* per the pattern-extraction discipline ([COR-007](../../decisions/core/COR-007-pattern-extraction.md)). #131 even names this exact "private intra-org capability sharing" driver. The 2026-07-03 conversation supplies that consumer (a real company wanting both forms above), which is what unblocks authoring the mechanism without violating extract-on-recurrence.

## What already exists (so the gap is narrow)

The **per-repo customisation seams are already first-class** — this is not missing:

- **The `project/` seam.** A capability = immutable kit-shipped logic/schemas + an adopter-owned `project/` directory ("the seam where adopter-specific values plug in", per the pm capability README). For `project-management`: `config.yaml`, `workstreams.yaml`, `hooks.yaml`, `hook-templates/`, `adapter-overlays/`.
- **Lifecycle hooks** ([project-management:DEC-024-lifecycle-hooks]) — real *behaviour* extension points (set-field / post-comment-from-template / custom script after lifecycle events), declared in adopter-owned `project/hooks.yaml`.
- **The agent overlay mechanism** ([COR-013](../../decisions/core/COR-013-agent-architecture.md) rule 5) — kit templates carry `<category>` placeholders resolved at deploy time against `.pkit/agents/project/overlay.yaml`.

All three preserve the no-shared-files invariant ([COR-001](../../decisions/core/COR-001-content-mechanisms.md)): the adopter never edits kit content; it layers on top. **The gap is not per-repo customisation — it is *sharing* adopter-owned content across many company repos.**

## The core insight — one need, two faces

The two asks (private capability; company overlay) are the **same underlying need**: a *private company-internal channel for distributing adopter-owned content*, pulled into each consuming repo, pinnable, reconciled against its source. A capability and an overlay/profile differ only in *what* travels; the *distribution* is identical. They should be designed together — one private-content source mechanism serving both — rather than as two bespoke pipes.

The natural shape mirrors [PRJ-004](../../decisions/project/PRJ-004-distribution-channel.md)'s git-URL philosophy, one altitude down (capability/overlay instead of the whole kit): a **private git source at a ref**, `install --from` (capability) / an overlay-fetch (profile), auth (SSH/PAT), version-pinning, and **per-source reconcile** on `sync`/`upgrade` (the distinct third reconciliation case COR-031 names — neither kit-source nor adopter-local, but an *external* source).

## Candidate shapes / alternatives

- **A — Private git source + `install --from` / overlay-fetch (favoured direction).** Mirrors PRJ-004; no new registry infra; privacy = repo access; sharing = anyone with access; versioning = source tags. The company's private source repo is *itself* a pkit adopter where the content is `incubated-in-repo`; other repos consume it as `externally-sourced`. Overlays travel the same way (fetch a `project/` bundle at a pinned ref).
- **B — Private package index (private PyPI / artifact registry).** Heavier infra; PRJ-004 already weighed and deferred registries at current scale. Revisit only if git-source auth/reconcile proves insufficient.
- **C — Company kit fork / overlay-bundle wheel.** The company builds its own wheel bundling private capabilities alongside public ones (leans on ADR-033 content-bundling). Heaviest — maintain a kit fork; loses clean upstream tracking. Explicitly *against* the layer-don't-fork principle.
- **Rejected framing — fork the capability to customise it.** For the overlay case, forking `project-management` loses upstream updates and fights no-shared-files. The idiom is **layer via the seams; if a needed customisation has no seam, add a seam to the capability (upstream), don't fork.**

Favoured: **A**, unifying capability-sources (#131) and overlay-sharing under one private-source mechanism.

## Forces

- **No-shared-files (COR-001) + upstream updates** pull hard toward *layer, don't fork*.
- **Extract-on-recurrence (COR-007)** — now satisfied for `externally-sourced`; the overlay-sharing half should show the same grounding before its own mechanism is built (this note is that grounding).
- **Distribution minimalism (PRJ-004)** — prefer git-URL over registries until scale forces otherwise; the private case should inherit that bias.
- **Seam sufficiency** — how much company customisation is reachable through *config + hooks + overlays* vs needing *new seams*? If common company needs exceed the current seams, the capability-extension-point vocabulary itself may need widening (a related but separable question).

## Composition with the release + versioning work (#332)

Distinct design area, but coherent with it:
- **Two independent, pinnable version axes** in a consuming repo: kit capability version (the kit's, pinned per project via the resolver) + the company overlay/capability version (from the private source). No fork ⇒ no capability-version divergence.
- The **private source repo running its own releases** is a candidate *second adopter* of the reusable "release discipline" the #332 review flagged as the deferred extractable — a future recurrence signal, not built now.

## Open questions

- Do capability-sources (#131) and overlay-sharing get **one unified record/mechanism**, or two coordinated records under a shared origin/source model? (Lean: shared mechanism, possibly two thin decisions over it.)
- **Overlay identity**: is a shared `project/` profile itself a first-class, named, versioned artifact (a "capability profile"), or just "adopter content fetched from a source"? What does its manifest look like?
- **Reconcile semantics** for an overlay: unlike a capability subtree, a `project/` bundle is *merged into* an adopter's own `project/` — how do company defaults compose with a repo's local overrides (precedence, three-way merge, conflict surfacing)?
- **Auth** in the resolver/CI path — SSH-agent vs PAT; how it degrades offline (consistent with the resolver's on-demand-fetch fallback under #332).
- **Seam-gap policy** — when a company need has no existing seam, what's the sanctioned path to add one upstream vs a temporary local override?

## Retirement (COR-012)

Retire by producing: the [EPIC #131] `externally-sourced` decision + an overlay-sharing decision — or, if the convergence holds, a single **private-content-distribution** record spanning both, over a shared external-source/origin model. Cross-refs to carry into whatever crystallises: COR-031, EPIC #131, COR-013, [project-management:DEC-024-lifecycle-hooks], PRJ-004, COR-001, COR-007, ADR-033.
