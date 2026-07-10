---
id: PRJ-007
title: The release step keeps the self-host backbone manifest current
status: accepted
date: 2026-07-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

When `pkit release apply` writes a new backbone version to `.pkit/VERSION`, it **also** writes that version to the source repo's own `.pkit/manifest.yaml` `backbone_version`, so this repo's self-host install record tracks the version it actually ships. This is project-kit-the-project's own release mechanics and is invisible to adopters (adopters never run `release apply`; their manifest is written by install/upgrade). It exists because the source repo self-hosts but never installs into itself, so its manifest's `backbone_version` had frozen at the repo's genesis value while `.pkit/VERSION` advanced — leaving `pkit status` permanently misreporting the self-host backbone.

## Context

The source repo self-hosts: its `.pkit/` is simultaneously the methodology **source** and a notional **install**. The manifest's `backbone_version` records "the backbone version synced into this `.pkit/`" — normally written by the install / sync / upgrade machinery. But the source repo never runs that machinery on itself, so its `.pkit/manifest.yaml` `backbone_version` stayed at the genesis value (`1.0.0`) while `.pkit/VERSION` advanced (to `1.142.4` when [#549] was raised). `pkit status` reads `backbone_version` from the manifest and so reported the self-host backbone as far behind ("run `pkit upgrade`") — a permanent, misleading display.

Since the version-provenance footer (the stamping policy of [project-management:DEC-041-version-provenance-stamp]) had its tree-version read fixed to prefer `.pkit/VERSION` in #545, `pkit status` display is the only remaining reader of the self-host `backbone_version` — so the drift was cosmetic but permanent. [#549] weighed three options: leave it (a self-host quirk), one-time correct it (re-rots at the next release), or make the release step own it (durable root-cause fix). This record pins the third.

## Decision

**`pkit release apply` writes the self-host `.pkit/manifest.yaml` `backbone_version` whenever it bumps the backbone.** Three points.

- **On a backbone bump, apply writes both files.** [PRJ-002] makes `release apply` the sole writer of version state on `main`; this record extends *what it writes*: when it writes a new backbone version to `.pkit/VERSION`, it writes the same value to `.pkit/manifest.yaml` `backbone_version`. A capability-only release (no backbone bump, `.pkit/VERSION` unchanged) leaves `backbone_version` untouched — consistent, because the backbone did not move.

- **Self-host-only mechanics; adopters unchanged.** Adopter manifests are still written by install / upgrade. Nothing in the adopter path changes. The field's meaning — "the backbone version this `.pkit/` is running" — holds under both writers: install/upgrade write it when an adopter syncs; `release apply` writes it when the source repo cuts its own backbone. This project accepts the two-writer arrangement as a deliberate consequence of self-hosting.

- **One-time reconciliation.** The change lands with a one-time set of the current self-host `backbone_version` to the current `.pkit/VERSION`, so `pkit status` reads correctly immediately rather than only after the next backbone-bumping release; `apply` maintains it thereafter.

## Rationale

**Why release-owns over leave-or-one-time.** *Leave* keeps a permanently-misleading `status` and a dead field that invites re-investigation (it already cost one — the #545 provenance dig traced back to this drift). *One-time correct* re-rots at the next release, since nothing would maintain it — effort spent for a value that goes stale again. *Release-owns* is the only durable fix: the release is the exact moment the source repo's backbone changes, so it is the natural and sole place to record it, mirroring how install/upgrade record it for adopters.

**Why a PRJ, not a COR/DEC/ADR.** This is project-kit-the-project's own release process — maintainer-facing, adopter-invisible (the release flow "is not propagated to adopters", per `.pkit/release/README.md`). Per [COR-014] universal applicability, self-hosting mechanics belong in the project namespace, not the core corpus.

**Why the two-writer arrangement is acceptable, not a smell.** One could object that a single field written by two different mechanisms (install/upgrade for adopters, release for the source) is inconsistent. But the field's *meaning* is stable — "the backbone version this install runs" — and the source repo is the one install whose backbone advances via `release`, not via a sync. Naming the arrangement here keeps a future maintainer from "fixing" one writer in ignorance of the other.

### Alternatives considered

- **Leave as-is.** Rejected — permanent misreport, dead field, recurring confusion.
- **One-time correction only.** Rejected — re-rots at the next release; no mechanism keeps it current.
- **Special-case `pkit status` to show `.pkit/VERSION` in the source repo.** Rejected — it fixes the *display* but leaves the stored field wrong for any future reader; better to keep the stored value true.

## Implications

- **`pkit release apply`** (in `src/project_kit/release.py`) gains a write of `.pkit/manifest.yaml` `backbone_version` = the new backbone version, on backbone-bumping releases. Keyed to the same condition as the `.pkit/VERSION` write.
- **A one-time reconciliation** sets the current self-host `backbone_version` to the current `.pkit/VERSION`.
- **`pkit status`** then reads a correct self-host backbone version (no spurious "run `pkit upgrade`").
- **Adopter install/upgrade paths are untouched**; this is source-repo-only behaviour.
- **Backbone surface change** → declared via a `backbone` changeset (per [PRJ-002]'s release-driven model); no adopter-facing behaviour changes.
- **Closes [#549]**; stands on PRJ-002, PRJ-004, COR-014 — all accepted.
