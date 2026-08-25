---
id: PRJ-009
title: project-kit dogfoods its own code-review panel
status: accepted
date: 2026-08-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The `software-engineering` capability ships a code-review panel — `code-reviewer`, `security-reviewer`, `docs-reviewer` — that registers into the merge gate through the pm reviewer-contribution socket ([project-management:DEC-032]) and blocks a code-carrying PR until the panel approves ([software-engineering:DEC-002]). It was built to close report #715: before it, the only shipped reviewer was conventions-only, so a merge gate could read `APPROVED` with zero code actually reviewed.

Building and shipping the panel (released in v1.149.0) did not turn it on for project-kit's *own* PRs — the capability collector reads a capability's `review-contributions.yaml` only when that capability is registered in `.pkit/manifest.yaml`'s `components:` list ([project-management:DEC-032] D5), and `software-engineering` was not registered here. So #715's exact gap stayed live on the repo that authored the fix: project-kit's PRs were gated only by the conventions reviewer.

## Decision

**Register the in-repo `software-engineering` capability into project-kit's own manifest so the code-review panel gates project-kit's own code-carrying PRs.** project-kit dogfoods the review discipline it ships.

- Registration is via `pkit capabilities register software-engineering` (COR-031's in-place register for a capability whose source *is* the working tree), not `install` (which copies from kit source). Origin is recorded `incubated-in-repo`.
- The panel's dependency — `project-management >=0.54.0` ([COR-030]), the version that ships the DEC-032 type-axis + `touches-code` diff floor the panel's activation relies on — is satisfied by the v1.149.0 release (pm 0.53.0 → 0.54.0) and by reconciling pm's stale installed record to the released version.
- No new capability content is authored here; this is a project-side configuration change turning on already-shipped, already-released functionality.

## Rationale

**Why dogfood.** A methodology that ships a review gate and does not run it on its own changes is not credible, and — more concretely — leaves #715's gap open on the one repo most likely to merge gate-mechanism code. Running the panel on project-kit's PRs is both the honesty position and the tightest feedback loop for tuning the reviewers (over-blocking shows up on our own work first).

**Why registration, not a source change.** The capability already ships and released; adopters who install `software-engineering` already get the panel. Turning it on *here* is purely project-kit's own install-state — the same gesture any adopter makes — so it belongs in project-kit's manifest, recorded as a project (PRJ) decision, not in core.

**Why the installed-record reconciliation was needed.** The COR-030 dependency gate reads a dependency's *installed* record. project-kit's pm installed record had frozen at 0.17.0 because `pkit capabilities upgrade` copies kit-source→adopter and cannot run on an in-repo capability (source and destination are the same directory). All three intervening pm migrations were already applied in-tree (workflow schema already v4; bootstrap stamp already present), so only the record's version number was stale; it was reconciled to the released 0.54.0.

## Implications

- **project-kit's code-carrying PRs now require the panel.** A PR whose diff touches any non-documentation file resolves `code-reviewer` + `security-reviewer` + `docs-reviewer` into the required-reviewer set (the `touches-code` floor); `docs-reviewer` also rides the `type:*` wildcard for classified docs-only PRs. Each must post a fresh `APPROVED` verdict ([project-management:DEC-028]) — or be waived per-reviewer with an audited `--bypass-reviewer` ([project-management:DEC-050]) — before `done-work` passes.
- **The panel agents deploy** via the claude-code adapter alongside the existing agents.
- **Self-host quirk recorded:** `pkit capabilities upgrade` does not work on an in-repo capability (same-dir copy); an in-place installed-record refresh is the gap. Reconciling by hand is the current workaround; a dedicated in-place refresh verb is a possible future addition if this recurs (COR-007).
- **Not an adopter surface change:** the capability and its behaviour shipped in v1.149.0; this only flips project-kit's own install-state, so it declares no changelog entry.

## Related

- EPIC #725 (the code-review discipline); report #715 (the gap this closes on our repo).
- [software-engineering:DEC-002] — the panel; [project-management:DEC-032] — the reviewer-contribution socket; [project-management:DEC-050] — the per-reviewer override; [project-management:DEC-028] — the verdict grammar the gate consumes.
- [COR-030] — capability dependencies; [COR-031] — in-repo capability registration.
