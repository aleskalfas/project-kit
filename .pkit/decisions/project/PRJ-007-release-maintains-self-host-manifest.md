---
id: PRJ-007
title: The release step keeps the self-host backbone manifest current
status: accepted
date: 2026-07-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

When `pkit release apply` writes a new backbone version to `.pkit/VERSION`, it **also** writes that version to the source repo's own `.pkit/manifest.yaml`, as its `backbone_version` and its `completed_version`, so this repo's self-host install record tracks the version it actually ships. This is project-kit-the-project's own release mechanics and is invisible to adopters (adopters never run `release apply`; their manifest's version keys are written by first install and a version transition of the backbone). It exists because the source repo self-hosts but never installs into itself, so its manifest's `backbone_version` had frozen at the repo's genesis value while `.pkit/VERSION` advanced — leaving `pkit status` permanently misreporting the self-host backbone.

## Context

The source repo self-hosts: its `.pkit/` is simultaneously the methodology **source** and a notional **install**. The manifest's `backbone_version` records the release whose content this `.pkit/` holds — normally written by the machinery that installs and upgrades a project. But the source repo never runs that machinery on itself, so its `.pkit/manifest.yaml` `backbone_version` stayed at the genesis value (`1.0.0`) while `.pkit/VERSION` advanced (to `1.142.4` when [#549] was raised). `pkit status` reads `backbone_version` from the manifest and so reported the self-host backbone as far behind ("run `pkit upgrade`") — a permanent, misleading display.

Since the version-provenance footer (the stamping policy of [project-management:DEC-041-version-provenance-stamp]) had its tree-version read fixed to prefer `.pkit/VERSION` in #545, `pkit status` display is the only remaining reader of the self-host `backbone_version` — so the drift was cosmetic but permanent. [#549] weighed three options: leave it (a self-host quirk), one-time correct it (re-rots at the next release), or make the release step own it (durable root-cause fix). This record pins the third.

## Decision

**`pkit release apply` writes the self-host `.pkit/manifest.yaml`'s `backbone_version` and `completed_version` whenever it bumps the backbone.** Three points.

- **On a backbone bump, apply writes both files.** [PRJ-002] makes `release apply` the sole writer of version state on `main`; this record extends *what it writes*: when it writes a new backbone version to `.pkit/VERSION`, it writes the same value to the manifest's `backbone_version` and `completed_version`. Each is an in-place edit of its own line, the completion's added beside the backbone's where the manifest has no `completed_version` line (ADR-065 point 3). A capability-only release (no backbone bump, `.pkit/VERSION` unchanged) leaves both keys untouched — consistent, because the backbone did not move.

- **Self-host-only mechanics; adopters unchanged.** In an adopter, the manifest's version keys are written by first install and a version transition of the backbone (ADR-065). This record changes nothing in the adopter path. The keys mean what [COR-059] points 1 and 6 say: `backbone_version` names the release whose content the `.pkit/` holds, or the target of an unfinished transition, and a project is at a version only when both keys name it. That holds under both kinds of writer: first install and a transition in an adopter, and `release apply` in the source repo. When the source repo cuts its own backbone, `release apply` writes the two keys equal. This project accepts the two-writer arrangement as a deliberate consequence of self-hosting.

- **One-time reconciliation.** The change lands with a one-time set of the current self-host `backbone_version` to the current `.pkit/VERSION`, so `pkit status` reads correctly immediately rather than only after the next backbone-bumping release; `apply` maintains it thereafter.

## Rationale

**Why release-owns over leave-or-one-time.** *Leave* keeps a permanently-misleading `status` and a dead field that invites re-investigation (it already cost one — the #545 provenance dig traced back to this drift). *One-time correct* re-rots at the next release, since nothing would maintain it — effort spent for a value that goes stale again. *Release-owns* is the only durable fix: the release is the exact moment the source repo's backbone changes, so it is the natural and sole place to record it, mirroring how first install and a transition record it for adopters.

**Why a PRJ, not a COR/DEC/ADR.** This is project-kit-the-project's own release process — maintainer-facing, adopter-invisible (the release flow "is not propagated to adopters", per `.pkit/release/README.md`). Per [COR-014] universal applicability, self-hosting mechanics belong in the project namespace, not the core corpus.

**Why the two-writer arrangement is acceptable, not a smell.** One could object that keys written by two kinds of writer (first install and the transition in an adopter, the release step in the source) are inconsistent. But their *meaning* is stable — the release the `.pkit/` is at, which both keys name once nothing is left unfinished — and the source repo is the one install whose backbone advances via `release`, not via a transition. The release writes `completed_version` too, though nothing in the source reads it, to keep the stored value true: a manifest with no completion reads as an unfinished transition whose migration history is unknown ([COR-059] point 6). Naming the arrangement here keeps a future maintainer from "fixing" one writer in ignorance of the other.

### Alternatives considered

- **Leave as-is.** Rejected — permanent misreport, dead field, recurring confusion.
- **One-time correction only.** Rejected — re-rots at the next release; no mechanism keeps it current.
- **Special-case `pkit status` to show `.pkit/VERSION` in the source repo.** Rejected — it fixes the *display* but leaves the stored field wrong for any future reader; better to keep the stored value true.

## Implications

- **`pkit release apply`** (in `src/project_kit/release.py`) gains a write of `.pkit/manifest.yaml`'s `backbone_version` and `completed_version` = the new backbone version, on backbone-bumping releases. Keyed to the same condition as the `.pkit/VERSION` write. Its list of what a release may write admits both lines.
- **A one-time reconciliation** sets the current self-host `backbone_version` to the current `.pkit/VERSION`.
- **`pkit status`** then reads a correct self-host backbone version (no spurious "run `pkit upgrade`").
- **The adopter's writers of the version keys, first install and a transition of the backbone, are untouched**; this is source-repo-only behaviour.
- **Backbone surface change** → declared via a `backbone` changeset (per [PRJ-002]'s release-driven model); no adopter-facing behaviour changes.
- **Closes [#549]**; stands on PRJ-002, PRJ-004, COR-014, COR-059 and ADR-065 — all accepted.
