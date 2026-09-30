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

**Decision-touching PRs declare a changeset, by the nature of the decision.** Adding or amending a COR / PRJ / ADR / DEC touches the methodology adopters receive (a new principle in an accepted COR, above), so a decision-only PR *does* declare a changeset — the guard fires on `.pkit/decisions/` deliberately. Which kind turns on one test — *can an adopter observe, or must they do something different, the moment this record syncs?*
- **Self-executing** decision (yes) — its text is itself the adopter-observable behaviour change, with no separate implementation to carry the declaration (amending a commit/branch convention, a PR-body rule). Declares a **real** changeset with a changelog entry.
- **Design-ahead** decision (no) — it records intent for a feature that ships in a later implementation PR (which carries the real changeset). Declares **`none`** — recorded, but no changelog line, so the changelog never advertises a feature adopters cannot yet use.
COR-041 (a reserved origin realised, mechanism deferred) is design-ahead → `none`; a change to COR-008's commit convention is self-executing → real. A blanket guard exemption for `.pkit/decisions/` was rejected: it is location-based, cannot tell the two apart, and would silently drop self-executing rule changes from the changelog.

**D1 — Surface changes are declared, not applied, per PR.** A surface-changing PR drops a *changeset file* — a small, collision-free-named file naming the affected `component → segment` (one of `patch` / `minor` / `major` / `none`) plus a human-readable note on what changed. The kit adopts `changie` for this. The PR carries the changeset; it does **not** edit `.pkit/VERSION`, a component's `version`, or `requires_backbone`. A component that comes to need a backbone says so in its changeset, and the release step raises its floor (D4).

**D2 — The bump segment is a human surface judgment, not a function of the commit type.** Which segment a change warrants — and which *tier* (backbone vs a specific component) it bumps — is a person's read of the surface impact, recorded in the changeset. It is *not* inferred from the conventional-commits type of the commit: a 20-commit analysis confirmed the CC type determines neither the segment nor which tier bumps (a `feat` may be a patch to one component or a minor to the backbone; a `fix` may be surface-breaking). Segment semantics follow semver: **patch** = backward-compatible fix to existing surface; **minor** = backward-compatible new surface; **major** = a breaking change to existing surface (available now that the kit is past 1.0).

**D3 — Version numbers are written only on `main`, by a release authority.** A *release PR* is the sole writer of version state. It consumes the pending changesets, computes each tier's new version from the current state on `main`, generates the changelog, writes the version numbers, and cuts the tags — via the existing `pkit version tag --push` (per PRJ-004, which already mandates annotated tags matching `.pkit/VERSION`; this reuses that mechanism and is not a new distribution decision). No other PR writes a version. The tagged `main` commit the release PR produces is the coherent state the version-locked official install is built from (ADR-033).

**D4 — `requires_backbone` is written at the release step, main-only: the upper bound broadens, a declared floor rises.** Auto-broadening kit-shipped components' `requires_backbone` upper bound (dogfooding the lifecycle compatibility model, so kit and components co-evolve in lockstep) moves out of a per-branch `version bump` and into the release step — so it, too, is written only on `main`. The broaden is widen-only: it raises an upper bound to cover the backbone, and never narrows one. The lower bound — the floor — moves only on declaration: a changeset names the backbone its component needs, and the release step raises that component's floor to the highest backbone its changesets name. A changeset names it one of two ways. **`release`** names the backbone the release ships, for a need on backbone surface not yet released: the new backbone when the release moves it, else the current one — which may lack the change the component needs (a backbone change declared `none`, or one merged after the component's), so the release step says so when it raises a floor to it in a release that does not move the backbone. **An explicit version** names a backbone that has shipped, for a need an older backbone already meets; it must be at or below the current backbone. The raise is raise-only and never automatic: no floor moves unless a changeset says its component needs it; such a changeset must move the component's version, since a raised floor changes what the component requires; and it rides on a change to that component — the changeset guard refuses one in a pull request whose diff does not touch the component's tree. A floor is raised only to a release version, never to a pre-release. The release step states each raised floor in the component's changelog entry.

The changeset-file **format** and the release-step **mechanics** (changeset naming, directory, the release command's exact behaviour) are **not** fixed here — they live in the release-flow spec shipped with the implementation (#464). This record carries the *policy*; the spec carries the *mechanics*.

## Rationale

**Why still trigger on surface changes.** The trigger is unchanged from the hybrid: the version moves for what an adopter could break against, not for docs / cleanup / internal churn. Tying the version to surface changes (rather than to every merged PR) is what keeps the number a compatibility signal instead of a commit counter. The promotion changes *when and where* the number is written, not *what* warrants a bump.

**Why declare-then-apply rather than bump inside the surface PR.** The hybrid put the bump commit *in* the surface PR, so every surface-changing branch wrote the same version cells (`.pkit/VERSION`, a component's `version`, `requires_backbone`). Parallel branches then collided on those cells at merge — a merge conflict on version numbers that carries no real semantic conflict (observed on PR #360). Recording *intent* in a per-PR changeset and letting a single release step compute the actual numbers removes the whole conflict class: two branches can each add their own changeset file without ever touching a shared version cell.

**Why version numbers are written only on `main`.** Making `main` the sole writer is the concurrency fix stated plainly: feature branches carry declarations, not numbers, so no feature branch can move the version out from under another. The release step reads the single source of truth (current `main`), computes forward from it, and writes once. This also keeps the version monotonic and auditable — every number has exactly one authoring commit, on `main`, with its changelog.

**Why a floor rises only on declaration, at the release.** The broaden can be automatic because releasing under a backbone asserts compatibility with it. A floor cannot be inferred that way: raising it asserts the component *no longer works* on an older backbone, which only the change's author knows — the release step cannot tell a component that started depending on new backbone behaviour from one that did not, and raising every floor on every backbone release would lock adopters out of component upgrades for nothing. Nor can the branch write the floor: D1 bars it from the cell, and a need on backbone surface not yet released names a version not computed until the release. Without the declaration the floor had no writer at all, so a component that stopped carrying something the new backbone took over could be installed on an older backbone that has neither. The declaration closes the gap: the author states the need on the branch, and the release — the one writer of version state — writes it into the floor.

**Why an explicit version, and why it is bounded by the current backbone.** `release` names a need to the patch of the backbone the release ships, so a need an older backbone already meets would be over-constrained: the component would be refused on every backbone between the two, for nothing, by the install and upgrade gates that read its `requires_backbone` and by an externally-sourced consumer's compatibility check (COR-041). The explicit version gives that need its own number. Bounded by the current backbone, the number names a backbone that exists — a fact the branch reads from its own `.pkit/VERSION` — rather than the release it would otherwise predict, the prediction D1 keeps off the branch. The bound holds from branch to release: the backbone on `main` only moves forward, so a version at or below the branch's backbone is at or below the release's too.

**Why the declaration rides on a change to its component.** A floor asserts that the component no longer works on an older backbone, which only the author of the change that creates the need knows. A changeset declaring a floor for a component its pull request leaves alone asserts an incompatibility no change in that pull request created, so the changeset guard, which already reads the pull request's diff, refuses it: the declaration arrives with the change that makes it true.

**Why the raised floor reaches the changelog.** A raised floor changes what an adopter must run the component on, and adopters learn what changed from the changelog. Stating the floor in the component's entry puts it where they read before upgrading the component, rather than only in a package file.

**Why the release step is backbone-internal, not a capability.** Releasing the backbone is a process the backbone depends on for its own existence, so by COR-010's anti-inversion principle it cannot be delegated to an opt-in, independently-versioned component. The release authority — the changeset-consuming, version-writing, tag-cutting step — stays in the backbone tier; it is not packaged as a capability an adopter might or might not install.

**Why the segment stays a human judgment.** The segment and the tier are a person's read of surface impact, not a mechanical function of the commit's conventional-commits type — a 20-commit analysis confirmed the CC type predicts neither. Automating the segment off the commit type would produce wrong bumps; the changeset makes the human call explicit and reviewable.

**Why tooling (`changie` + a release step) over manual edits.** The release work — consuming changesets, computing each tier forward, broadening `requires_backbone`, generating the changelog, cutting tags — is exactly the mechanical, error-prone, recurring shape COR-007 says to invest tooling in, rather than re-deriving it by hand each release. `changie` is the adopted changeset tool; the release-step command is project tooling that owns the write.

### Alternatives considered

- **Keep bumping inside the surface PR (the pre-1.0 hybrid).** Retired — parallel branches conflict on shared version cells (PR #360). Declaring intent per-PR and applying on `main` removes the conflict class.
- **Per-PR bump on every merged PR.** Rejected — version stops being a compatibility signal and becomes a commit counter.
- **Infer the segment from the conventional-commits type.** Rejected — a 20-commit analysis showed CC type determines neither the segment nor which tier bumps.
- **Raise floors automatically on a backbone release, or let the branch write them.** Rejected — the first claims an incompatibility nobody observed; the second writes a version cell D1 bars, and for a need on backbone surface not yet released, with a number the branch cannot know.
- **The changeset names any explicit minimum, including one above the current backbone.** Rejected — a version above the current backbone is a number predicted on the branch, the prediction D1 keeps off it, and wrong whenever the release lands differently; `release` names that backbone without predicting it. Bounded by the current backbone, the explicit version is kept (D4): it names a backbone that has shipped, and without it a need an older backbone meets is over-constrained to the current one. An outside author releasing their own capability is not bound by D1 and edits their own floor.
- **Let a changeset declare a floor for any component.** Rejected — a floor asserts an incompatibility only the change that creates it can know, so a declaration with no change to its component behind it is a floor raised by hand under a changeset's name. The changeset guard ties the declaration to a diff that touches the component's tree.
- **Package the release step as a capability.** Rejected — inverts the two-tier dependency direction (COR-010); the backbone's own release process must stay backbone-internal.
- **Calver instead of semver.** Rejected by COR-010 (semver is the kit-wide rule).
- **No policy; bump ad-hoc when it "feels right".** Rejected — drift; reviewers cannot dispatch on a stable definition of "surface change".

## Implications

- **Feature-branch PRs declare, they do not write.** A surface-changing PR adds a changeset file and edits no version cell (`.pkit/VERSION`, a component's `version`, `requires_backbone`). Whether the bump script (`pkit version bump <segment>`) survives as an internal step the release authority calls, or is folded into the release command, is a mechanics question owned by the release-flow spec (#464), not this record.
- **The release step writes versions on `main`.** A release PR consumes the pending changesets, computes each tier forward, broadens kit-shipped components' `requires_backbone` upper bounds (so kit and components co-evolve in lockstep), raises the floor of each component a changeset declares needs a backbone, generates the changelog — stating each raised floor in its component's entry — and cuts tags via `pkit version tag --push` (PRJ-004). It is the only writer of version state; no feature branch touches version cells.
- **Capability promotion emits a changeset too.** When a capability is promoted from adopter-incubated origin (COR-031) into kit source (EPIC #131), the promotion is a surface change like any other: it drops the promoted capability's first changeset, so the release step records that capability's initial version in kit source.
- **`.github/PULL_REQUEST_TEMPLATE.md`** carries a checklist item: "Surface change? If yes, add a changeset (see PRJ-002)." Reviewers flag PRs that look like surface changes but shipped no changeset (or vice versa).
- **Commits** use conventional-commits format per COR-008. Changeset-adding commits and the release PR's commit conventions are detailed in the release-flow spec (#464).
- **The lifecycle README's worked example** uses fictional version numbers (`v2.1.0`, etc.) for illustrative breadth; this policy applies only to the actual `.pkit/VERSION` of project-kit-the-project.
