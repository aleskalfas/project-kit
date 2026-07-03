---
id: PRJ-002
title: Version-bump policy for project-kit (declared, release-driven)
status: accepted
date: 2026-05-08
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

COR-010 fixes that backbone and components use semver, components declare `requires_backbone` ranges, and migrations land per `<major>.<minor>.0/`. What COR-010 deliberately does *not* cover — because it is project-neutral — is *when* the source kit's backbone version actually bumps and *who* performs the bump. That is a project-kit-the-project policy.

`.pkit/VERSION` declares the current backbone version (`0.1.0` today). Without a bump policy, every PR creates ambiguity: should this change bump the backbone? Which segment? Per-PR with no rule risks two failure modes — version churn (every doc-fix bumps; the number stops meaning anything) or version freeze (nothing bumps; the number stops tracking reality). Either way the version stops being a useful compatibility signal for the lifecycle machinery.

Mid-conversation alternatives were considered: bump on every merged PR (too noisy pre-1.0); bump only at "release moments" (requires a release concept the kit does not yet have); calver instead of semver (rejected by COR-010). This record's founding hybrid was one path; the policy has since been promoted post-1.0 to the declared, release-driven Decision below (see the Mode line).

## Decision

**Mode: declared per-PR, applied release-driven, written main-only** (promoted from the pre-1.0 hybrid on 2026-07-03). A **surface change** is still what moves the version — but it is now *declared* on the PR that lands it and *applied* later, only on `main`, by a release step. Feature branches never write a version number.

A **surface change** is anything an adopter could observe, depend on, or break against:

- A new CLI command or subcommand.
- A new principle in an accepted COR (or any new COR).
- A breaking change to an existing CLI / spec / contract.
- A new area, area variant, or component type.
- A schema change to manifests / `package.yaml` / `.pkit/VERSION`.
- A new convention adopters are expected to follow (e.g., the git-conventions and PR-workflow records of COR-008 / COR-009).

A **non-surface change** moves no version: documentation refinement where the contract is unchanged, internal refactors adopters do not see, behaviour-preserving bug fixes, test-only changes, new PRJ records, and README cross-reference updates that follow already-landed surface changes.

**D1 — Surface changes are declared, not applied, per PR.** A surface-changing PR drops a *changeset file* — a small, collision-free-named file naming the affected `component → segment` (one of `patch` / `minor` / `major` / `none`) plus a human-readable note on what changed. The kit adopts `changie` for this. The PR carries the changeset; it does **not** edit `.pkit/VERSION`, a component's `version`, or `requires_backbone`.

**D2 — The bump segment is a human surface judgment, not a function of the commit type.** Which segment a change warrants — and which *tier* (backbone vs a specific component) it bumps — is a person's read of the surface impact, recorded in the changeset. It is *not* inferred from the conventional-commits type of the commit: a 20-commit analysis confirmed the CC type determines neither the segment nor which tier bumps (a `feat` may be a patch to one component or a minor to the backbone; a `fix` may be surface-breaking). Segment semantics follow semver: **patch** = backward-compatible fix to existing surface; **minor** = backward-compatible new surface; **major** = a breaking change to existing surface (available now that the kit is past 1.0).

**D3 — Version numbers are written only on `main`, by a release authority.** A *release PR* is the sole writer of version state. It consumes the pending changesets, computes each tier's new version from the current state on `main`, generates the changelog, writes the version numbers, and cuts the tags — via the existing `pkit version tag --push` (per PRJ-004, which already mandates annotated tags matching `.pkit/VERSION`; this reuses that mechanism and is not a new distribution decision). No other PR writes a version. The tagged `main` commit the release PR produces is the coherent state the version-locked official install is built from (ADR-033).

**D4 — `requires_backbone` broadening happens at the release step, main-only.** Auto-broadening kit-shipped components' `requires_backbone` upper bound (dogfooding the lifecycle compatibility model, so kit and components co-evolve in lockstep) moves out of a per-branch `version bump` and into the release step — so it, too, is written only on `main`.

The changeset-file **format** and the release-step **mechanics** (changeset naming, directory, the release command's exact behaviour) are **not** fixed here — they live in the release-flow spec shipped with the implementation (#464). This record carries the *policy*; the spec carries the *mechanics*.

## Rationale

**Why still trigger on surface changes.** The trigger is unchanged from the hybrid: the version moves for what an adopter could break against, not for docs / cleanup / internal churn. Tying the version to surface changes (rather than to every merged PR) is what keeps the number a compatibility signal instead of a commit counter. The promotion changes *when and where* the number is written, not *what* warrants a bump.

**Why declare-then-apply rather than bump inside the surface PR.** The hybrid put the bump commit *in* the surface PR, so every surface-changing branch wrote the same version cells (`.pkit/VERSION`, a component's `version`, `requires_backbone`). Parallel branches then collided on those cells at merge — a merge conflict on version numbers that carries no real semantic conflict (observed on PR #360). Recording *intent* in a per-PR changeset and letting a single release step compute the actual numbers removes the whole conflict class: two branches can each add their own changeset file without ever touching a shared version cell.

**Why version numbers are written only on `main`.** Making `main` the sole writer is the concurrency fix stated plainly: feature branches carry declarations, not numbers, so no feature branch can move the version out from under another. The release step reads the single source of truth (current `main`), computes forward from it, and writes once. This also keeps the version monotonic and auditable — every number has exactly one authoring commit, on `main`, with its changelog.

**Why the release step is backbone-internal, not a capability.** Releasing the backbone is a process the backbone depends on for its own existence, so by COR-010's anti-inversion principle it cannot be delegated to an opt-in, independently-versioned component. The release authority — the changeset-consuming, version-writing, tag-cutting step — stays in the backbone tier; it is not packaged as a capability an adopter might or might not install.

**Why the segment stays a human judgment.** The segment and the tier are a person's read of surface impact, not a mechanical function of the commit's conventional-commits type — a 20-commit analysis confirmed the CC type predicts neither. Automating the segment off the commit type would produce wrong bumps; the changeset makes the human call explicit and reviewable.

**Why tooling (`changie` + a release step) over manual edits.** The release work — consuming changesets, computing each tier forward, broadening `requires_backbone`, generating the changelog, cutting tags — is exactly the mechanical, error-prone, recurring shape COR-007 says to invest tooling in, rather than re-deriving it by hand each release. `changie` is the adopted changeset tool; the release-step command is project tooling that owns the write.

### Alternatives considered

- **Keep bumping inside the surface PR (the pre-1.0 hybrid).** Retired — parallel branches conflict on shared version cells (PR #360). Declaring intent per-PR and applying on `main` removes the conflict class.
- **Per-PR bump on every merged PR.** Rejected — version stops being a compatibility signal and becomes a commit counter.
- **Infer the segment from the conventional-commits type.** Rejected — a 20-commit analysis showed CC type determines neither the segment nor which tier bumps.
- **Package the release step as a capability.** Rejected — inverts the two-tier dependency direction (COR-010); the backbone's own release process must stay backbone-internal.
- **Calver instead of semver.** Rejected by COR-010 (semver is the kit-wide rule).
- **No policy; bump ad-hoc when it "feels right".** Rejected — drift; reviewers cannot dispatch on a stable definition of "surface change".

## Implications

- **Feature-branch PRs declare, they do not write.** A surface-changing PR adds a changeset file and edits no version cell (`.pkit/VERSION`, a component's `version`, `requires_backbone`). Whether the bump script (`pkit version bump <segment>`) survives as an internal step the release authority calls, or is folded into the release command, is a mechanics question owned by the release-flow spec (#464), not this record.
- **The release step writes versions on `main`.** A release PR consumes the pending changesets, computes each tier forward, broadens kit-shipped components' `requires_backbone` upper bounds (so kit and components co-evolve in lockstep), generates the changelog, and cuts tags via `pkit version tag --push` (PRJ-004). It is the only writer of version state; no feature branch touches version cells.
- **Capability promotion emits a changeset too.** When a capability is promoted from adopter-incubated origin (COR-031) into kit source (EPIC #131), the promotion is a surface change like any other: it drops the promoted capability's first changeset, so the release step records that capability's initial version in kit source.
- **`.github/PULL_REQUEST_TEMPLATE.md`** carries a checklist item: "Surface change? If yes, add a changeset (see PRJ-002)." Reviewers flag PRs that look like surface changes but shipped no changeset (or vice versa).
- **Commits** use conventional-commits format per COR-008. Changeset-adding commits and the release PR's commit conventions are detailed in the release-flow spec (#464).
- **The lifecycle README's worked example** uses fictional version numbers (`v2.1.0`, etc.) for illustrative breadth; this policy applies only to the actual `.pkit/VERSION` of project-kit-the-project.
